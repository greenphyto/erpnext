import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, get_datetime, get_time

import erpnext
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
from erpnext.stock.doctype.batch.batch import set_batch_nos


class DeliveryNoteGP(DeliveryNote):
    def __init__(self, *args, **kwargs):
        super(DeliveryNoteGP, self).__init__(*args, **kwargs)
        if not cint(self.is_return):
            field_args = {
                "source_dt": "Delivery Note Item",
                "target_dt": "Sales Order Item",
                "join_field": "so_detail",
                "target_field": "delivered_qty",
                "target_parent_dt": "Sales Order",
                "target_parent_field": "per_delivered",
                "target_ref_field": "qty",
                "source_field": "qty",
                "percent_join_field": "against_sales_order",
                "status_field": "delivery_status",
                "keyword": "Delivered",
                "second_source_dt": "Sales Invoice Item",
                "second_source_field": "qty",
                "second_join_field": "so_detail",
                "overflow_type": "delivery",
                "second_source_extra_cond": """ and exists(select name from `tabSales Invoice`
                    where name=`tabSales Invoice Item`.parent and update_stock = 1)""",
                "extra_cond": " and qty > 0",
            }
            self.status_updater = [field_args]
            self.status_updater.extend(
                [
                    {
                        "source_dt": "Delivery Note Item",
                        "target_dt": "Sales Invoice Item",
                        "join_field": "si_detail",
                        "target_field": "billed_qty",
                        "target_parent_dt": "Sales Invoice",
                        "target_parent_field": "per_billed",
                        "target_ref_field": "stock_qty",
                        "source_field": "stock_qty",
                        "percent_join_field": "against_sales_invoice",
                        "overflow_type": "delivery",
                        "no_allowance": 1,
                    },
                ]
            )

    def before_insert(self):
        super(DeliveryNoteGP, self).before_insert()
        if self.is_return:
            self.naming_series = "DO-RET-.YYYY.-.###"

    def validate(self):
        self.validate_non_stock()
        super(DeliveryNoteGP, self).validate()
        self.update_reff_order()
        self.validate_donation()
        self.validate_replacement()
        self.add_item_batch_foms_id()
        self.validate_pledge()
        if not self.is_return:
            set_batch_nos(self, "warehouse", throw=True)
            set_batch_nos(self, "warehouse", throw=True, child_table="packed_items")
        try:
            self.link_internal_company()
        except Exception:
            pass

    def on_submit(self):
        super(DeliveryNoteGP, self).on_submit()
        self.clear_foms_id()
        try:
            self.set_other_reff()
        except Exception:
            pass

    def validate_non_stock(self):
        if not self.non_stock_item:
            return
        for d in self.get("items"):
            d.warehouse = ""
        self.set_warehouse = ""

    def validate_pledge(self):
        if self.customer == "Donor":
            self.is_pledge = 1
            if not self.contact_display:
                self.contact_display = self.donor_name

    def validate_donation(self):
        if self.is_donation and not self.organization_name:
            frappe.throw("Organization name must be set for Donation.")
        if self.is_pledge and not self.donor_name:
            frappe.throw("Donor name must be set for pledge purpose.")

        account = None
        if self.is_donation:
            account = frappe.get_value("Company", self.company, "donation_account")
        elif self.is_giveaway:
            account = frappe.get_value("Company", self.company, "giveaway_account")
        elif self.is_replacement:
            account = frappe.get_value("Company", self.company, "sales_replacement_account")
        elif self.is_production:
            account = frappe.get_value("Company", self.company, "production_delivery_account")
        elif self.is_marketing:
            account = frappe.get_value("Company", self.company, "marketing_delivery_account")
        elif self.is_pledge:
            account = frappe.get_value("Company", self.company, "donor_delivery_account")

        if account:
            for d in self.items:
                d.expense_account = account

    def validate_replacement(self):
        if not cint(self.is_replacement):
            return
        if not self.replacement_reason:
            frappe.throw(_("Please provide a reason for the replacement quantity."))

    def add_item_batch_foms_id(self):
        for d in self.get("items"):
            if not d.batch_no:
                continue
            d.foms_lot_name, d.foms_work_order = self._get_foms_lot(d.batch_no) or ("", "")

    def _get_foms_lot(self, batch):
        temp = frappe.db.sql(
            """
            SELECT w.foms_lot_name, w.foms_work_order
            FROM `tabStock Ledger Entry` s
            LEFT JOIN `tabStock Entry` se ON se.name = s.voucher_no
            LEFT JOIN `tabWork Order` w ON w.name = se.work_order
            WHERE s.batch_no = %s AND s.is_cancelled = 0 AND se.purpose = 'Manufacture'
        """,
            batch,
            as_dict=1,
        )
        if temp:
            return temp[0].foms_lot_name, temp[0].foms_work_order
        else:
            lot_id = frappe.db.get_value("Batch", batch, "foms_lot_id")
            return lot_id, ""

    def update_reff_order(self):
        so_list = []
        si_list = []
        for d in self.get("items"):
            if d.against_sales_order:
                so_list.append(d.against_sales_order)
            if d.against_sales_invoice:
                si_list.append(d.against_sales_invoice)
        self.sales_order_no = ", ".join(list(set(so_list)))
        self.sales_invoice_no = ", ".join(list(set(si_list)))
        self.get_sales_order_delivery_date()

    def get_sales_order_delivery_date(self):
        delivery_date = []
        for d in self.get("items"):
            if d.against_sales_order:
                deliv_date = frappe.get_value(
                    "Sales Order", d.against_sales_order, "delivery_date"
                )
                if deliv_date:
                    delivery_date.append(deliv_date)
        if not self.delivery_date and delivery_date:
            self.delivery_date = min(delivery_date)

    def link_internal_company(self):
        if not self.is_internal_customer:
            return

        so_number = next(
            (d.against_sales_order for d in self.items if d.against_sales_order), None
        )
        if not so_number:
            return

        inter_po_name = frappe.get_value(
            "Sales Order", so_number, "inter_company_order_reference"
        )
        if not inter_po_name:
            inter_po_name = frappe.db.get_value(
                "Sales Order",
                {"inter_company_order_reference": so_number, "docstatus": 1},
                "name",
            )
            if not inter_po_name:
                return
            frappe.db.set_value(
                "Sales Order",
                so_number,
                "inter_company_order_reference",
                inter_po_name,
            )

        represents_company = frappe.get_value(
            "Sales Order", so_number, "represents_company"
        )
        inter_pr_number = frappe.db.sql(
            """
            SELECT DISTINCT dni.parent
            FROM `tabDelivery Note Item` dni
            JOIN `tabDelivery Note` dn ON dn.name = dni.parent
            WHERE dn.docstatus = 1 AND dni.against_sales_order = %s
            ORDER BY dn.creation DESC LIMIT 1
        """,
            inter_po_name,
            as_dict=False,
        )

        if not inter_pr_number:
            return

        inter_pr_number = inter_pr_number[0][0]
        if inter_pr_number:
            frappe.db.set_value(
                "Purchase Receipt",
                inter_pr_number,
                "inter_company_reference",
                self.name,
            )
        self.inter_company_reference = inter_pr_number
        self.represents_company = represents_company

    def clear_foms_id(self):
        if self.foms_id:
            self.foms_id = None

    def set_other_reff(self):
        invoice = False
        for d in self.get("items"):
            if d.get("si_detail"):
                so_detail, so_name = frappe.get_value(
                    "Sales Invoice Item",
                    {"name": d.si_detail, "docstatus": 1},
                    ["so_detail", "sales_order"],
                ) or (None, None)
                if so_detail:
                    d.so_detail = so_detail
                    d.against_sales_order = so_name
                    frappe.db.set_value(
                        "Sales Invoice",
                        d.against_sales_invoice,
                        "delivery_note",
                        self.name,
                    )
            elif d.get("so_detail"):
                si_detail, si_name = frappe.get_value(
                    "Sales Invoice Item",
                    {"so_detail": d.so_detail, "docstatus": 1},
                    ["name", "parent"],
                ) or (None, None)
                if si_detail:
                    frappe.db.set_value(
                        "Sales Invoice Item", si_detail, "dn_detail", d.name
                    )
                    frappe.db.set_value(
                        "Sales Invoice Item",
                        si_detail,
                        "delivery_note",
                        d.parent,
                    )
                    frappe.db.set_value(
                        "Sales Invoice", si_name, "delivery_note", self.name
                    )
                    d.si_detail = si_detail
                    d.against_sales_invoice = si_name
                    invoice = True

        if invoice:
            self.per_billed = 100

    def close_request_form(self):
        for d in self.get("items"):
            batch = d.batch_no
            if not batch:
                continue
            reff_no = frappe.db.sql(
                """
                SELECT name, voucher_no, SUM(actual_qty) AS qty, actual_qty as total_qty
                FROM `tabStock Ledger Entry`
                WHERE batch_no = %s AND is_cancelled = 0
            """,
                batch,
                as_dict=1,
            )
            if reff_no:
                for reff in reff_no:
                    work_order = frappe.db.get_value(
                        "Stock Entry", reff.voucher_no, "work_order"
                    )
                    if not work_order:
                        continue
                    reff_so, reff_req = frappe.db.get_value(
                        "Work Order", work_order, ["sales_order_no", "request_no"]
                    ) or ("", "")
                    if reff_req:
                        for no in reff_req.strip().split(","):
                            percent = (reff.total_qty - reff.qty) / reff.total_qty * 100
                            doc = frappe.get_doc("Request", no)
                            for row in doc.get("items"):
                                if row.item_code == d.item_code:
                                    row.db_set("delivery_percent", percent)
                            doc.set_delivery_percent(db_update=True)


@frappe.whitelist()
def load_returned_data(filters):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    cond = ""
    if filters.get("customer"):
        cond += " AND so.customer = %(customer)s "
    if filters.get("item_code"):
        cond += " AND soi.item_code = %(item_code)s "
    return frappe.db.sql(
        """
        SELECT soi.name, so.name as so_number, so.customer, soi.item_code,
               soi.qty, soi.returned_qty, soi.replacement_qty as repl_qty,
               soi.returned_qty - soi.replacement_qty as repl_approx_qty
        FROM `tabSales Order Item` soi
        LEFT JOIN `tabSales Order` so ON so.name = soi.parent
        WHERE so.docstatus = 1 AND soi.returned_qty > 0 {cond}
    """.format(cond=cond),
        filters,
        as_dict=1,
    )
