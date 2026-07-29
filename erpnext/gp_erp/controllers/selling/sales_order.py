import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, getdate

import erpnext
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder


class SalesOrderGP(SalesOrder):
    def validate(self):
        super(SalesOrderGP, self).validate()
        self.validate_pledge()
        self.load_bom_items()

    def before_validate(self):
        super(SalesOrderGP, self).before_validate()
        self.validate_packaging()

    def on_submit(self):
        super(SalesOrderGP, self).on_submit()
        self.update_po_no()

    def on_cancel(self):
        self.check_work_order()
        super(SalesOrderGP, self).on_cancel()
        self.validate_working_progress(throw=1)

    def validate_pledge(self):
        if self.is_pledge and not self.donor_name:
            frappe.throw("Donor name must be set for pledge purpose.")
            if not self.contact_display:
                self.contact_display = self.donor_name

    def validate_packaging(self):
        for d in self.get("items"):
            pass

    def validate_po(self):
        if self.pending_po:
            self.po_no = "Pending PO"
            self.po_date = ""
            return

        if self.is_pledge:
            self.po_no = "For Pledge"
            self.po_date = ""
            return

        super(SalesOrderGP, self).validate_po()

    def update_po_no(self):
        old_doc = self.get_doc_before_save()
        if not old_doc:
            return

        if self.po_no != old_doc.get("po_no") or self.po_date != old_doc.get("po_date"):
            data = frappe.db.sql(
                """
                SELECT i.parent as name, i.item_code, count(d.name), po_no
                FROM `tabDelivery Note Item` i
                LEFT JOIN `tabDelivery Note` d ON d.name = i.parent
                WHERE i.against_sales_order IS NOT NULL and i.against_sales_order = %s
                GROUP BY d.name, d.po_no
            """,
                (self.name),
                as_dict=1,
            )
            for d in data:
                frappe.db.set_value(
                    "Delivery Note", d.name, "po_no", self.get("po_no") or ""
                )
                frappe.db.set_value(
                    "Delivery Note",
                    d.name,
                    "po_date",
                    getdate(self.po_date or ""),
                )

    def validate_working_progress(self, throw=False):
        progress = False
        for d in self.get("items"):
            if d.get("lot_id"):
                if throw:
                    frappe.throw(
                        _(
                            f"Cannot cancel {self.name} because already working in progress"
                        )
                    )
                return True
        return False

    def check_work_order(self):
        wo_list = frappe.db.get_list(
            "Work Order",
            {"sales_order_no": ["like", "%%" + self.name + "%%"], "docstatus": 1},
        )
        if wo_list:
            wo_str = ", ".join([x.name for x in wo_list])
            frappe.throw(
                _(
                    f"Cannot cancel Sales Order {self.name} becuase already linked to Work Order {wo_str}"
                )
            )

    def load_bom_items(self):
        self.bom_item = []
        for d in self.items:
            is_salad, bom_name = frappe.get_value(
                "Item", d.item_code, ["salad_product", "default_bom"]
            )
            if not is_salad:
                continue

            bom = frappe.get_doc("BOM", bom_name)
            for item in bom.get("items"):
                row = self.append("bom_item")
                row.item_code = item.item_code
                row.qty = item.qty * d.qty
                row.stock_qty = item.stock_qty * d.qty
                row.conversion_factor = item.conversion_factor
                row.uom = item.uom
                row.rate = item.rate
                row.amount = item.amount * item.qty
                row.bom = bom.name
                row.parent_item = d.item_code
                row.bom_no = frappe.get_value("Item", row.item_code, "default_bom")
                if not row.bom_no:
                    row.progress = 100

    def update_work_order_reference(self, wo_no, item):
        for d in self.get("items"):
            if d.item_code == item:
                d.lot_id = wo_no
                d.db_update()
        self.on_progress = 1

    def update_work_progress(self, item, qty):
        per_working = 0
        for d in self.get("items"):
            if d.item_code == item:
                per_working += 1
                d.work_order_qty = qty
                d.db_update()
        self.per_working = per_working / len(self.items) * 100


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_packaging_available(doctype, txt, searchfield, start, page_len, filters):
    item = filters.get("item")
    if txt:
        text = " and packaging like {} ".format(
            frappe.db.escape("%{0}%".format(txt))
        )
    else:
        text = ""
    query = """select packaging from `tabPackaging List Available`
        where parent = {item} {txt}""".format(
        txt=text, item=frappe.db.escape(item)
    )
    res = frappe.db.sql(query, filters, debug=0, as_list=1)
    return res
