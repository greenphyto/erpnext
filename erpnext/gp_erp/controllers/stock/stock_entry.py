import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, getdate, get_link_to_form

import erpnext
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.doctype.batch.batch import get_batch_qty


class StockEntryGP(StockEntry):
    def validate(self):
        super(StockEntryGP, self).validate()
        self.valdiate_from_supplier()
        self.validate_batch_splitting()
        self.validate_cost_center()
        self.calculate_wip_operation_cost()
        self.validate_wip_additional_cost()
        self.validate_stock_entry_asset()

    def on_submit(self):
        super(StockEntryGP, self).on_submit()
        self.create_asset_stock()
        self.set_close_materials()

    def on_cancel(self):
        self.validate_scrap_entry_from_work_order()
        super(StockEntryGP, self).on_cancel()
        self.set_close_materials()

    def valdiate_from_supplier(self):
        if self.purpose == "Material Receipt" and not self.from_supplier:
            frappe.throw(_("Supplier must be set for new stock receipt"))

    def validate_cost_center(self):
        from erpnext.accounts.utils import get_cost_center_from_account

        for d in self.items:
            res = get_cost_center_from_account(d.expense_account, self.company)
            cost_center = res.get("value")
            if cost_center or res.get("lock"):
                d.cost_center = cost_center

        for d in self.additional_costs:
            res = get_cost_center_from_account(d.expense_account, self.company)
            cost_center = res.get("value")
            if cost_center or res.get("lock"):
                d.cost_center = cost_center

    def validate_batch_splitting(self):
        if not self.purpose == "Material Transfer":
            return

        enable_split = frappe.db.get_single_value(
            "Stock Settings", "block_batch_splitting_transaction"
        )
        if enable_split:
            for d in self.get("items"):
                if not d.batch_no:
                    continue
                if d.consignment_request:
                    continue
                batch_source_qty = get_batch_qty(d.batch_no, d.s_warehouse, d.item_code)
                if d.transfer_qty < batch_source_qty:
                    frappe.throw(
                        _(
                            f"Row {d.idx}, Cannot move stock partially for batch {d.batch_no}, you can only move all qty as {batch_source_qty} {d.uom}"
                        )
                    )

    def calculate_wip_operation_cost(self):
        total_cost = 0
        for d in self.get("wip_additional_costs") or []:
            d.exchange_rate = d.exchange_rate or 1
            d.base_amount = flt(d.amount) * flt(d.exchange_rate)
            total_cost += d.base_amount
        self.total_wip_additional_costs = total_cost

    def validate_wip_additional_cost(self):
        total = 0
        for d in self.get("wip_additional_costs") or []:
            total += flt(d.base_amount)
        self.total_wip_additional_costs = total

    def validate_stock_entry_asset(self):
        if self.stock_entry_type_view != "Conversion from Inventory to Fixed Asset":
            return
        self.validate_asset_expense()

    def validate_asset_expense(self):
        for d in self.items:
            d.expense_account = d.asset_code
            d.item_asset = frappe.get_value("Item", {"asset_for_item": d.item_code})
            if not d.asset_category:
                default = frappe.get_value(
                    "Asset Code Map",
                    {"parent": "Accounts Settings", "account": d.asset_code},
                    "default_asset_category",
                )
                if not default:
                    frappe.throw(_(f"Row {d.idx}, missing Asset Category"))
                else:
                    d.asset_category = default

    def create_asset_stock(self):
        if self.stock_entry_type_view != "Conversion from Inventory to Fixed Asset":
            return
        for d in self.get("items"):
            asset_item = frappe.get_value("Item", {"asset_for_item": d.item_code})
            if not asset_item:
                ref_item = frappe.get_doc("Item", d.item_code)
                asset_name = d.item_code + " - asset"
                item = frappe.new_doc("Item")
                item.item_code = asset_name
                item.item_group = ref_item.item_group
                item.stock_uom = ref_item.stock_uom
                item.asset_for_item = d.item_code
                item.asset_code = d.asset_code
                item.asset_category = d.asset_category
                item.is_stock_item = 0
                item.is_fixed_asset = 1
                item.valuation_rate = d.basic_rate
                item.is_purchase_item = 0
                item.insert()

    def validate_scrap_entry_from_work_order(self):
        if not self.work_order and self.purpose != "Material Transfer for Manufacture":
            return

        try:
            from erpnext.controllers.foms import get_previous_operation

            prev_opr = get_previous_operation(self.operation)
            se_name = frappe.db.get_value(
                "Stock Entry",
                {
                    "docstatus": 1,
                    "work_order": self.work_order,
                    "stock_entry_type": "Material Issue",
                    "operation": prev_opr,
                },
                "name",
            )
            if se_name:
                link_name = get_link_to_form("Stock Entry", se_name)
                frappe.throw(
                    _(
                        f"Please cancel Scrap Material ({link_name}) from previous operation first, before cancel this Stock Entry"
                    )
                )
        except ImportError:
            pass

    def set_close_materials(self):
        if self.is_return and not self.work_order:
            return

        wo_qty = frappe.get_value("Work Order", self.work_order, "qty")
        if self.fg_completed_qty != wo_qty:
            return

        cancel = self.docstatus == 2
        if not cancel:
            frappe.db.set_value(
                "Work Order", self.return_work_order, "material_returned", 1
            )
        else:
            frappe.db.set_value(
                "Work Order", self.return_work_order, "material_returned", 0
            )

    def validate_purpose(self):
        if self.stock_entry_type_view:
            self.stock_entry_type = frappe.get_value(
                "Stock Entry Type", self.stock_entry_type_view, "purpose"
            )
        super(StockEntryGP, self).validate_purpose()

    def validate_finished_goods(self):
        production_item, wo_qty, finished_items = None, 0, []

        if not self.work_order:
            return

        wo_details = frappe.db.get_value(
            "Work Order", self.work_order, ["production_item", "qty"]
        )
        if wo_details:
            production_item, wo_qty = wo_details

        total_finish = 0
        for d in self.get("items"):
            if d.is_finished_item:
                if not self.work_order:
                    continue
                if d.item_code != production_item:
                    frappe.throw(
                        _("Finished Item {0} does not match with Work Order {1}").format(
                            d.item_code, self.work_order
                        )
                    )
                total_finish += d.transfer_qty
                finished_items.append(d.item_code)

        self.fg_completed_qty = total_finish

        if not finished_items:
            frappe.throw(
                msg=_("There must be atleast 1 Finished Good in this Stock Entry").format(
                    self.name
                ),
                title=_("Finished Good Not Found"),
                exc=FinishedGoodError,
            )

        allowance_percentage = flt(
            frappe.db.get_single_value(
                "Manufacturing Settings", "overproduction_percentage_for_work_order"
            )
        )

        if not allowance_percentage:
            return

        allowed_qty = wo_qty + ((allowance_percentage / 100) * wo_qty)

        if self.purpose == "Manufacture" and not self.is_return:
            if self.fg_completed_qty > allowed_qty:
                frappe.throw(
                    _(
                        "For quantity ({0}) should not exceed the quantity to manufacture ({1}) in Work Order {2}"
                    ).format(self.fg_completed_qty, allowed_qty, self.work_order)
                )

    def get_gl_entries(self, warehouse_account):
        from erpnext.accounts.general_ledger import process_gl_map

        gl_entries = super(StockEntryGP, self).get_gl_entries(warehouse_account)

        if self.purpose in ["Material Transfer for Manufacture", "Manufacture"] and self.is_return == 0:
            try:
                from erpnext.controllers.foms import (
                    get_cost_center,
                    get_previous_operation,
                    get_default_wip_account,
                )
                from erpnext.stock import get_item_account

                if self.purpose == "Material Transfer for Manufacture":
                    prev_operation = get_previous_operation(self.operation)
                    cost_center = get_cost_center(self.operation, self.company)
                    remarks = "From Previous WIP"
                    do_not_merge = 1
                else:
                    prev_operation = "Harvesting"
                    cost_center = ""
                    remarks = "Rate Variance"
                    do_not_merge = 0

                wip_account = get_item_account(
                    warehouse_account, "WIP", None, get_default=1, operation=prev_operation
                )
                prev_wip = self.get_previous_ledger_entry(wip_account)
                if prev_wip:
                    prev_wip = prev_wip[0]
                    if prev_wip.name:
                        expense_account = prev_wip.account
                        debit_amount = prev_wip.amount
                        if self.purpose == "Material Transfer for Manufacture":
                            variance_account = get_item_account(
                                warehouse_account,
                                "WIP",
                                "account",
                                get_default=1,
                                operation=self.operation,
                            )
                            for d in gl_entries:
                                if d.account == variance_account:
                                    d.remarks = "Additional/Activity Costs"

                        elif self.purpose == "Manufacture":
                            variance_account = frappe.get_value(
                                "Company", self.company, "default_cost_expense_account"
                            )
                            total_amount = 0
                            for gl in gl_entries:
                                if gl.account == prev_wip.account:
                                    if gl.credit:
                                        total_amount += gl.credit
                                    else:
                                        total_amount -= gl.debit
                            debit_amount = prev_wip.amount - flt(total_amount, 2)

                        if debit_amount:
                            row = self.get_gl_dict(
                                {
                                    "account": expense_account,
                                    "against": variance_account,
                                    "cost_center": cost_center,
                                    "remarks": remarks,
                                    "debit": -1 * debit_amount,
                                    "do_not_merge": do_not_merge,
                                },
                                account_currency=frappe.get_value(
                                    "Account", variance_account, "account_currency"
                                ),
                            )
                            gl_entries.append(row)

                            row = self.get_gl_dict(
                                {
                                    "account": variance_account,
                                    "against": expense_account,
                                    "cost_center": cost_center,
                                    "remarks": remarks,
                                    "debit": 1 * debit_amount,
                                    "do_not_merge": 0,
                                },
                                account_currency=frappe.get_value(
                                    "Account", variance_account, "account_currency"
                                ),
                            )
                            gl_entries.append(row)
            except ImportError:
                pass

        return process_gl_map(gl_entries, merge_entries=1)

    def get_previous_ledger_entry(self, wip_account):
        prev_wip = frappe.db.sql(
            """
            SELECT
                gl.name,
                s.name AS se_name,
                SUM(gl.debit) - SUM(gl.credit) AS amount,
                gl.account
            FROM
                `tabGL Entry` gl
                    LEFT JOIN
                `tabStock Entry` s ON gl.voucher_no = s.name
            WHERE
                s.work_order = %s
                    AND s.docstatus = 1
                    AND gl.account = %s
                    AND gl.voucher_no != %s
                    AND gl.posting_date <= %s
        """,
            (self.work_order, wip_account, self.name, self.posting_date),
            as_dict=1,
            debug=0,
        )
        return prev_wip


@frappe.whitelist()
def create_asset_from_stock_entry(se_name):
    import math

    se_doc = frappe.get_doc("Stock Entry", se_name)
    company = erpnext.get_default_company()

    def create_asset(item, date, asset_code, asset_category, purchase_value):
        doc = frappe.new_doc("Asset")
        asset_item = frappe.get_value("Item", {"asset_for_item": item})
        doc.company = company
        doc.item_code = asset_item
        doc.asset_name = item
        doc.is_existing_asset = 1
        doc.gross_purchase_amount = purchase_value
        doc.purchase_date = getdate(date)
        doc.available_for_use_date = getdate(date)
        doc.flags.ignore_mandatory = 1
        doc.insert()
        return doc.name

    result = "<p>Creating Asset as a Draft:</p><ul>"

    for d in se_doc.get("items"):
        if d.created_asset:
            temp_create = cstr(d.created_asset).split(",")
        else:
            temp_create = []

        already_create = []
        for x in temp_create:
            if frappe.get_value("Asset", x):
                already_create.append(x)

        qty_create = math.ceil(d.qty) - len(already_create)
        for x in already_create:
            result += f"<li>{d.item_code}: <b>{x}</b></li>"

        for i in range(qty_create):
            name = create_asset(
                d.item_code,
                se_doc.posting_date,
                d.asset_code,
                d.asset_category,
                d.purchase_value,
            )
            already_create.append(name)
            result += f"<li>{d.item_code}: <b>{name}</b></li>"

        str_data = ",".join(already_create)
        d.db_set("created_asset", str_data)

    asset_cdt = get_link_to_form("Asset", "Asset").replace("/Asset", "")
    result += f"</ul><p>Please go to the {asset_cdt}, and submit the newly created Asset document."
    frappe.msgprint(result)


@frappe.whitelist()
def get_item_expense_for_issue(item_code="", company=""):
    item = frappe.db.sql(
        """select i.name, i.stock_uom, i.description, i.image, i.item_name, i.item_group,
            i.has_batch_no, i.sample_quantity, i.has_serial_no, i.allow_alternative_item,
            id.expense_account, id.buying_cost_center
        from `tabItem` i LEFT JOIN `tabItem Default` id ON i.name=id.parent and id.company=%s
        where i.name=%s
            and i.disabled=0
            and (i.end_of_life is null or i.end_of_life<'1900-01-01' or i.end_of_life > %s)""",
        (company, item_code, frappe.utils.nowdate()),
        as_dict=1,
    )

    if not item:
        frappe.throw(
            _("Item {0} is not active or end of life has been reached").format(item_code)
        )

    item = item[0]
    from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults

    item_group_defaults = get_item_group_defaults(item.name, company)

    expense_account = (
        item.get("expense_account")
        or item_group_defaults.get("expense_account")
        or frappe.get_cached_value("Company", company, "default_expense_account")
    )
    return expense_account


class FinishedGoodError(frappe.ValidationError):
    pass
