# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, cstr, getdate

import erpnext
from erpnext.controllers.status_updater import StatusUpdater
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.stock_controller import get_warehouse_account_map
from erpnext.accounts.utils import get_fiscal_year
from erpnext.utilities.transaction_base import TransactionBase


class LazadaDelivery(TransactionBase):
    """Standalone delivery document for Lazada channel.

    Handles stock movement (SLE) and accounting (GL/COGS) independently
    from Delivery Note. Supports linking to Sales Order and Sales Invoice.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_updater = self._build_status_updater()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def before_insert(self):
        if not self.naming_series:
            self.naming_series = "LAZ-.YYYY.-.###"
        if not self.customer:
            self.customer = frappe.db.get_single_value("Lazada Settings", "lazada_customer")

    def set_missing_values(self, for_validate=False):
        if not self.customer:
            self.customer = frappe.db.get_single_value("Lazada Settings", "lazada_customer")
        if not self.set_warehouse and self.company:
            self.set_warehouse = frappe.db.get_value("Company", self.company, "default_warehouse")
        if not self.set_target_warehouse:
            self.set_target_warehouse = frappe.db.get_single_value("Lazada Settings", "default_warehouse")
        self.apply_target_warehouse_default()

    def validate(self):
        self.validate_posting_time()

        self.apply_target_warehouse_default()
        self.validate_warehouse()
        self.validate_items()
        self.validate_uom_is_integer("stock_uom", "stock_qty")
        self.validate_uom_is_integer("uom", "qty")
        self.validate_return()
        self.update_current_stock()
        self.calculate_totals()
        self.set_status()

    def on_submit(self):
        self.validate_packed_qty()
        self.update_prevdoc_status()
        self.update_stock_ledger()
        self.make_gl_entries()
        self.repost_future_sle_and_gle()

    def on_cancel(self):
        self.validate_cancellation()
        self.update_prevdoc_status()
        self.update_stock_ledger()
        self.make_gl_entries_on_cancel()
        self.repost_future_sle_and_gle()
        self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Repost Item Valuation")

    # ------------------------------------------------------------------
    # Warehouse defaults
    # ------------------------------------------------------------------

    def apply_target_warehouse_default(self):
        default_source = self.get("set_warehouse")
        default_target = self.get("set_target_warehouse")
        for item in self.get("items"):
            if default_source and not item.warehouse:
                item.warehouse = default_source
            if default_target and not item.target_warehouse:
                item.target_warehouse = default_target

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_warehouse(self):
        warehouses = list(set(d.warehouse for d in self.get("items") if getattr(d, "warehouse", None)))
        target_warehouses = list(
            set([d.target_warehouse for d in self.get("items") if getattr(d, "target_warehouse", None)])
        )
        warehouses.extend(target_warehouses)

        for w in warehouses:
            validate_disabled_warehouse(w)
            validate_warehouse_company(w, self.company)

        for d in self.get("items"):
            is_stock_item = frappe.db.get_value("Item", d.item_code, "is_stock_item") == 1
            if is_stock_item:
                if not d.warehouse:
                    frappe.throw(_("Source Warehouse required for stock item {0} in row {1}").format(d.item_code, d.idx))
                if not d.target_warehouse:
                    frappe.throw(_("Target Warehouse required for stock item {0} in row {1}").format(d.item_code, d.idx))
                if d.warehouse == d.target_warehouse:
                    frappe.throw(
                        _("Row {0}: Source Warehouse and Target Warehouse cannot be the same").format(d.idx)
                    )

    def validate_items(self):
        for d in self.get("items"):
            is_stock_item = frappe.db.get_value("Item", d.item_code, "is_stock_item") == 1
            if is_stock_item and not d.stock_uom:
                frappe.throw(_("Row {0}: Stock UOM is required for stock item {1}").format(d.idx, d.item_code))

    def validate_return(self):
        if self.is_return:
            if not self.return_against:
                frappe.throw(_("Return Against is required for return delivery"))
            original = frappe.db.get_value("Lazada Delivery", self.return_against, ["docstatus", "is_return"], as_dict=1)
            if not original:
                frappe.throw(_("Return Against Lazada Delivery {0} does not exist").format(self.return_against))
            if original.docstatus != 1:
                frappe.throw(_("Return Against Lazada Delivery {0} is not submitted").format(self.return_against))
            if original.is_return:
                frappe.throw(_("Return Against Lazada Delivery {0} is itself a return").format(self.return_against))

    def validate_packed_qty(self):
        pass

    def validate_cancellation(self):
        pass

    # ------------------------------------------------------------------
    # Calculations
    # ------------------------------------------------------------------

    def update_current_stock(self):
        if self.get("_action") and self._action != "update_after_submit":
            for d in self.get("items"):
                if d.target_warehouse:
                    d.actual_qty = frappe.db.get_value(
                        "Bin", {"item_code": d.item_code, "warehouse": d.target_warehouse}, "actual_qty"
                    )

    def calculate_totals(self):
        self.total_qty = 0
        self.total = 0
        self.base_total = 0
        for d in self.get("items"):
            if d.qty:
                if flt(d.conversion_factor) == 0.0:
                    d.conversion_factor = (
                        get_conversion_factor(d.item_code, d.uom).get("conversion_factor") or 1.0
                    )
                d.stock_qty = flt(d.qty) * flt(d.conversion_factor)
                d.amount = flt(d.qty) * flt(d.rate)
                d.base_amount = d.amount * flt(self.conversion_rate)
            else:
                d.stock_qty = 0
                d.amount = 0
                d.base_amount = 0
            self.total_qty += flt(d.stock_qty)
            self.total += flt(d.amount)
            self.base_total += flt(d.base_amount)

        # Calculate taxes
        self.total_taxes_and_charges = 0
        self.base_total_taxes_and_charges = 0
        for t in self.get("taxes"):
            if t.rate:
                t.tax_amount = flt(self.total) * flt(t.rate) / 100
                t.base_tax_amount = t.tax_amount * flt(self.conversion_rate)
            self.total_taxes_and_charges += flt(t.tax_amount)
            self.base_total_taxes_and_charges += flt(t.base_tax_amount)

        self.grand_total = self.total + self.total_taxes_and_charges
        self.base_grand_total = self.base_total + self.base_total_taxes_and_charges

    def set_status(self):
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 1:
            if self.is_return:
                self.status = "Return"
            else:
                self.status = "Submitted"
        elif self.docstatus == 2:
            self.status = "Cancelled"

    # ------------------------------------------------------------------
    # Stock Ledger
    # ------------------------------------------------------------------

    def get_item_list(self):
        il = []
        for d in self.get("items"):
            il.append(
                frappe._dict(
                    {
                        "warehouse": d.warehouse,
                        "item_code": d.item_code,
                        "qty": d.stock_qty,
                        "uom": d.uom,
                        "stock_uom": d.stock_uom,
                        "conversion_factor": d.conversion_factor,
                        "batch_no": cstr(d.get("batch_no")).strip(),
                        "serial_no": cstr(d.get("serial_no")).strip(),
                        "name": d.name,
                        "target_warehouse": d.target_warehouse,
                        "company": self.company,
                        "voucher_type": self.doctype,
                        "allow_zero_valuation": d.allow_zero_valuation_rate,
                        "incoming_rate": d.get("incoming_rate"),
                        "item_row": d,
                    }
                )
            )
        return il

    def update_stock_ledger(self):
        sl_entries = []
        for d in self.get_item_list():
            if frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1 and flt(d.qty):
                if flt(d.conversion_factor) == 0.0:
                    d.conversion_factor = (
                        get_conversion_factor(d.item_code, d.uom).get("conversion_factor") or 1.0
                    )

                if not d.warehouse:
                    frappe.throw(_("Source Warehouse is required in row {0}").format(d.idx))

                if not d.target_warehouse:
                    frappe.throw(_("Target Warehouse is required in row {0}").format(d.idx))

                # Posting order depends on is_return (same as DN logic)
                if d.warehouse and (
                    (not cint(self.is_return) and self.docstatus == 1)
                    or (cint(self.is_return) and self.docstatus == 2)
                ):
                    sl_entries.append(self.get_sle_for_source_warehouse(d))

                if d.target_warehouse:
                    sl_entries.append(self.get_sle_for_target_warehouse(d))

                if d.warehouse and (
                    (not cint(self.is_return) and self.docstatus == 2)
                    or (cint(self.is_return) and self.docstatus == 1)
                ):
                    sl_entries.append(self.get_sle_for_source_warehouse(d))

        self.make_sl_entries(sl_entries)

    def get_sle_for_source_warehouse(self, item_row):
        sle = self.get_sl_entries(
            item_row,
            {
                "actual_qty": -1 * flt(item_row.qty),
                "incoming_rate": item_row.incoming_rate,
                "recalculate_rate": cint(self.is_return),
            },
        )
        if item_row.target_warehouse and not cint(self.is_return):
            sle.dependant_sle_voucher_detail_no = item_row.name
        return sle

    def get_sle_for_target_warehouse(self, item_row):
        sle = self.get_sl_entries(
            item_row, {"actual_qty": flt(item_row.qty), "warehouse": item_row.target_warehouse}
        )
        if self.docstatus == 1:
            if not cint(self.is_return):
                sle.update({"incoming_rate": item_row.incoming_rate, "recalculate_rate": 1})
            else:
                sle.update({"outgoing_rate": item_row.incoming_rate})
                if item_row.warehouse:
                    sle.dependant_sle_voucher_detail_no = item_row.name
        return sle

    def get_sl_entries(self, item_row, args):
        sl_dict = frappe._dict(
            {
                "item_code": item_row.get("item_code"),
                "warehouse": item_row.get("warehouse"),
                "posting_date": self.posting_date,
                "posting_time": self.posting_time,
                "fiscal_year": get_fiscal_year(self.posting_date, company=self.company)[0],
                "voucher_type": self.doctype,
                "voucher_no": self.name,
                "voucher_detail_no": item_row.name,
                "actual_qty": (self.docstatus == 1 and 1 or -1) * flt(item_row.get("stock_qty")),
                "stock_uom": frappe.db.get_value("Item", item_row.get("item_code"), "stock_uom"),
                "incoming_rate": 0,
                "company": self.company,
                "batch_no": cstr(item_row.get("batch_no")).strip(),
                "serial_no": item_row.get("serial_no"),
                "project": item_row.get("project") or self.get("project"),
                "is_cancelled": 1 if self.docstatus == 2 else 0,
            }
        )
        sl_dict.update(args)
        return sl_dict

    def make_sl_entries(self, sl_entries, allow_negative_stock=False, via_landed_cost_voucher=False):
        from erpnext.stock.stock_ledger import make_sl_entries as _make_sl_entries
        _make_sl_entries(sl_entries, allow_negative_stock, via_landed_cost_voucher)

    def repost_future_sle_and_gle(self):
        pass

    # ------------------------------------------------------------------
    # Accounting (GL Entries)
    # ------------------------------------------------------------------

    def make_gl_entries(self, gl_entries=None, from_repost=False):
        if self.docstatus == 2:
            make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

        if not cint(erpnext.is_perpetual_inventory_enabled(self.company)):
            return

        if self.docstatus == 1:
            if not gl_entries:
                gl_entries = self.get_gl_entries()
            if gl_entries:
                make_gl_entries(gl_entries, from_repost=from_repost)

    def make_gl_entries_on_cancel(self):
        if frappe.db.sql(
            """select name from `tabGL Entry` where voucher_type=%s and voucher_no=%s""",
            (self.doctype, self.name),
        ):
            self.make_gl_entries()

    def get_gl_entries(self):
        warehouse_account = get_warehouse_account_map(self.company)
        sle_map = self.get_stock_ledger_details()
        gl_entries = []
        precision = self.get_debit_field_precision()

        for item_row in self.get("items"):
            sle_list = sle_map.get(item_row.name)
            if not sle_list:
                continue

            for sle in sle_list:
                if not warehouse_account.get(sle.warehouse):
                    continue

                stock_value_difference = flt(sle.stock_value_difference)
                expense_account = item_row.expense_account
                if not expense_account:
                    frappe.throw(
                        _("Expense Account is required for item {0} in row {1}").format(
                            item_row.item_code, item_row.idx
                        )
                    )

                warehouse_account_name = warehouse_account.get(sle.warehouse, {}).get("account")
                if not warehouse_account_name:
                    frappe.throw(
                        _("Warehouse {0} is not linked to any account").format(sle.warehouse)
                    )

                # Debit warehouse asset account
                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": warehouse_account_name,
                            "against": expense_account,
                            "cost_center": item_row.cost_center,
                            "remarks": self.remarks or _("Accounting Entry for Stock"),
                            "debit": flt(stock_value_difference, precision),
                        },
                        item=item_row,
                    )
                )

                # Credit expense/COGS account
                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": expense_account,
                            "against": warehouse_account_name,
                            "cost_center": item_row.cost_center,
                            "remarks": _("Accounting Entry for Stock"),
                            "debit": -1 * flt(stock_value_difference, precision),
                        },
                        item=item_row,
                    )
                )

        return gl_entries

    def get_stock_ledger_details(self):
        stock_ledger = {}
        stock_ledger_entries = frappe.db.sql(
            """
            select
                name, warehouse, stock_value_difference, valuation_rate,
                voucher_detail_no, item_code, posting_date, posting_time,
                actual_qty, qty_after_transaction
            from
                `tabStock Ledger Entry`
            where
                voucher_type=%(doctype)s and voucher_no=%(name)s and is_cancelled = 0
            """,
            {"doctype": self.doctype, "name": self.name},
            as_dict=True,
        )
        for sle in stock_ledger_entries:
            stock_ledger.setdefault(sle.voucher_detail_no, []).append(sle)
        return stock_ledger

    def get_gl_dict(self, args, account_currency=None, item=None):
        from erpnext.accounts.doctype.account.account import get_account_currency
        from erpnext.controllers.accounts_controller import get_accounting_dimensions
        from erpnext.controllers.accounts_controller import set_balance_in_account_currency

        posting_date = args.get("posting_date") or self.get("posting_date")
        fiscal_years = get_fiscal_year(posting_date, company=self.company)
        fiscal_year = fiscal_years[0][0] if len(fiscal_years) == 1 else None

        company_currency = frappe.db.get_value("Company", self.company, "default_currency")

        gl_dict = frappe._dict(
            {
                "company": self.company,
                "posting_date": posting_date,
                "fiscal_year": fiscal_year,
                "voucher_type": self.doctype,
                "voucher_no": self.name,
                "remarks": self.get("remarks") or self.get("remark"),
                "debit": 0,
                "credit": 0,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": 0,
                "is_opening": self.get("is_opening") or "No",
                "party_type": None,
                "party": None,
                "project": self.get("project"),
            }
        )

        accounting_dimensions = get_accounting_dimensions()
        dimension_dict = frappe._dict()
        for dimension in accounting_dimensions:
            dimension_dict[dimension] = self.get(dimension)
            if item and item.get(dimension):
                dimension_dict[dimension] = item.get(dimension)
        gl_dict.update(dimension_dict)
        gl_dict.update(args)

        if not account_currency and gl_dict.get("account"):
            account_currency = get_account_currency(gl_dict.account)

        if gl_dict.account:
            set_balance_in_account_currency(
                gl_dict, account_currency, self.get("conversion_rate"), company_currency
            )

        return gl_dict

    def get_debit_field_precision(self):
        return frappe.get_precision("GL Entry", "debit")

    # ------------------------------------------------------------------
    # Status Updater — SO/SI qty tracking
    # ------------------------------------------------------------------

    def _build_status_updater(self):
        updaters = []

        if not cint(self.is_return):
            updaters.append(
                {
                    "source_dt": "Lazada Delivery Item",
                    "target_dt": "Sales Order Item",
                    "join_field": "so_detail",
                    "target_field": "delivered_qty",
                    "target_parent_dt": "Sales Order",
                    "target_ref_field": "qty",
                    "source_field": "qty",
                    "percent_join_field": "against_sales_order",
                    "overflow_type": "delivery",
                    "extra_cond": " and qty > 0",
                }
            )
            updaters.append(
                {
                    "source_dt": "Lazada Delivery Item",
                    "target_dt": "Sales Invoice Item",
                    "join_field": "si_detail",
                    "target_field": "delivered_qty",
                    "target_parent_dt": "Sales Invoice",
                    "target_ref_field": "qty",
                    "source_field": "qty",
                    "percent_join_field": "against_sales_invoice",
                    "overflow_type": "delivery",
                    "no_allowance": 1,
                }
            )

        if cint(self.is_return):
            updaters.append(
                {
                    "source_dt": "Lazada Delivery Item",
                    "target_dt": "Sales Order Item",
                    "join_field": "so_detail",
                    "target_field": "returned_qty",
                    "target_parent_dt": "Sales Order",
                    "source_field": "-1 * qty",
                    "extra_cond": """ and exists (select name from `tabLazada Delivery`
                        where name=`tabLazada Delivery Item`.parent and is_return=1)""",
                }
            )
            updaters.append(
                {
                    "source_dt": "Lazada Delivery Item",
                    "target_dt": "Lazada Delivery Item",
                    "join_field": "ld_detail",
                    "target_field": "returned_qty",
                    "target_parent_dt": "Lazada Delivery",
                    "target_parent_field": "per_returned",
                    "target_ref_field": "stock_qty",
                    "source_field": "-1 * stock_qty",
                    "percent_join_field_parent": "return_against",
                }
            )

        return updaters

    def update_prevdoc_status(self):
        self.update_qty()

    def update_qty(self, update_modified=True):
        for args in self.status_updater:
            if self.docstatus == 1:
                args["cond"] = " or parent='%s'" % self.name.replace('"', '"')
            else:
                args["cond"] = " and parent!='%s'" % self.name.replace('"', '"')
            self._update_children(args, update_modified)
            if "percent_join_field" in args or "percent_join_field_parent" in args:
                self._update_percent_field_in_targets(args, update_modified)

    def _update_children(self, args, update_modified):
        for d in self.get_all_children():
            if d.doctype != args["source_dt"]:
                continue

            self._update_modified(args, update_modified)
            args["detail_id"] = d.get(args["join_field"])
            frappe.db.sql(
                """update `tab{target_dt}`
                set {target_field} = (select ifnull(sum({source_field}), 0)
                    from `tab{source_dt}`
                    where {join_field} = %(detail_id)s {cond})
                where name = %(detail_id)s""".format(**args),
                args,
            )

    def _update_percent_field_in_targets(self, args, update_modified):
        if "percent_join_field" in args:
            target_parent_dt = args["target_parent_dt"]
            percent_field = args.get("target_parent_field")
            if not percent_field:
                continue_data = frappe.db.get_value(
                    target_parent_dt, self.get(args["percent_join_field"]), ["per_billed", "docstatus"], as_dict=1
                )
                if continue_data and continue_data.docstatus == 1:
                    return
            if percent_field:
                target_parent_field = args.get("target_parent_field")
                if target_parent_field:
                    ref_field = args.get("target_ref_field", "qty")
                    args["ref_field"] = ref_field
                    frappe.db.sql(
                        """update `tab{target_parent_dt}` set {target_parent_field} =
                            (select ifnull(sum(`tab{target_dt}`.{target_field}), 0)
                            from `tab{target_dt}`
                            where `tab{target_dt}`.{percent_join_field} = `tab{target_parent_dt}`.name)
                            / (select ifnull(sum({ref_field}), 1)
                            from `tab{source_dt}`
                            where `tab{source_dt}`.{percent_join_field} = `tab{target_parent_dt}`.name)
                            where name = (select {percent_join_field} from `tab{source_dt}`
                            where `tab{source_dt}`.name = %(detail_id)s)""".format(**args),
                        args,
                    )

    def _update_modified(self, args, update_modified):
        pass

    # ------------------------------------------------------------------
    # Return
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def make_return(source_name, target_doc=None):
        source = frappe.get_doc("Lazada Delivery", source_name)

        def update_item(source_doc, target_doc, source_parent):
            target_doc.qty = source_doc.qty
            target_doc.is_return = 1

        def postprocess(source, target):
            target.is_return = 1
            target.return_against = source.name
            target.set_warehouse = source.set_warehouse
            target.set_target_warehouse = source.set_target_warehouse
            for row in target.get("items"):
                row.ld_detail = source.items[row.idx - 1].name
                row.is_return = 1

        doclist = get_mapped_doc(
            "Lazada Delivery",
            source_name,
            {
                "Lazada Delivery": {
                    "doctype": "Lazada Delivery",
                    "field_map": {},
                },
                "Lazada Delivery Item": {
                    "doctype": "Lazada Delivery Item",
                    "field_map": {
                        "name": "ld_detail",
                    },
                    "postprocess": update_item,
                },
            },
            target_doc,
            postprocess,
            ignore_permissions=1,
        )
        return doclist

    # ------------------------------------------------------------------
    # SO Mapping
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def make_lazada_delivery(source_name, target_doc=None):
        def update_item(source_doc, target_doc, source_parent):
            target_doc.against_sales_order = source_doc.parent
            target_doc.so_detail = source_doc.name
            if not target_doc.description:
                target_doc.description = source_doc.description or source_doc.item_name or source_doc.item_code or ""

        def postprocess(source, target):
            target.customer = frappe.db.get_single_value("Lazada Settings", "lazada_customer") or source.customer
            target.company = source.company
            target.set_target_warehouse = frappe.db.get_single_value("Lazada Settings", "default_warehouse")
            default_expense = frappe.db.get_value("Company", target.company, "default_expense_account")
            default_cost_center = frappe.db.get_value("Company", target.company, "cost_center")
            # Set tax template
            tax_template = frappe.db.get_value("Sales Taxes and Charges Template", {"company": target.company}, "name")
            if tax_template:
                target.taxes_and_charges = tax_template
                target.taxes = []
                tax_rows = frappe.get_all("Sales Taxes and Charges",
                    filters={"parent": tax_template},
                    fields=["charge_type", "account_head", "rate", "cost_center", "description"],
                    order_by="idx asc"
                )
                for t in tax_rows:
                    target.append("taxes", t)
            for row in target.get("items"):
                if not row.warehouse:
                    row.warehouse = frappe.db.get_value("Company", target.company, "default_warehouse")
                row.target_warehouse = target.set_target_warehouse
                if not row.description:
                    row.description = row.item_name or row.item_code or ""
                if not row.expense_account and default_expense:
                    row.expense_account = default_expense
                if not row.cost_center and default_cost_center:
                    row.cost_center = default_cost_center
            target.set_warehouse = target.items[0].warehouse if target.items else None

        doclist = get_mapped_doc(
            "Sales Order",
            source_name,
            {
                "Sales Order": {
                    "doctype": "Lazada Delivery",
                    "field_map": {},
                },
                "Sales Order Item": {
                    "doctype": "Lazada Delivery Item",
                    "field_map": {},
                    "postprocess": update_item,
                    "condition": lambda doc: doc.qty > doc.delivered_qty,
                },
            },
            target_doc,
            postprocess,
            ignore_permissions=1,
        )
        return doclist

    # ------------------------------------------------------------------
    # SI Mapping
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def make_sales_invoice(source_name, target_doc=None):
        def update_item(source_doc, target_doc, source_parent):
            target_doc.against_lazada_delivery = source_doc.parent
            target_doc.ld_detail = source_doc.name
            target_doc.warehouse = source_doc.warehouse

        def postprocess(source, target):
            target.customer = source.customer
            target.company = source.company
            target.update_stock = 1
            # Set taxes from source LD or from template
            if source.taxes_and_charges:
                target.taxes_and_charges = source.taxes_and_charges
                target.taxes = []
                for t in source.taxes:
                    target.append("taxes", {
                        "charge_type": t.charge_type,
                        "account_head": t.account_head,
                        "rate": t.rate,
                        "cost_center": t.cost_center,
                        "description": t.description,
                    })
            elif not target.taxes_and_charges:
                tax_template = frappe.db.get_value("Sales Taxes and Charges Template",
                    {"company": target.company}, "name")
                if tax_template:
                    target.taxes_and_charges = tax_template
                    tax_rows = frappe.get_all("Sales Taxes and Charges",
                        filters={"parent": tax_template},
                        fields=["charge_type", "account_head", "rate", "cost_center", "description"],
                        order_by="idx asc"
                    )
                    for t in tax_rows:
                        target.append("taxes", t)

        doclist = get_mapped_doc(
            "Lazada Delivery",
            source_name,
            {
                "Lazada Delivery": {
                    "doctype": "Sales Invoice",
                    "field_map": {},
                },
                "Lazada Delivery Item": {
                    "doctype": "Sales Invoice Item",
                    "field_map": {},
                    "postprocess": update_item,
                },
            },
            target_doc,
            postprocess,
            ignore_permissions=1,
        )
        return doclist
