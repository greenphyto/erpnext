import frappe
from frappe import _
from frappe.utils import cint

from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import StockReconciliation


class StockReconciliationGP(StockReconciliation):
    def before_save(self):
        if self.purpose == "Opening Stock":
            for d in self.items:
                if not d.batch_no:
                    exists = frappe.get_value("Batch", {"item": d.item_code})
                    if exists:
                        d.batch_no = exists
                    else:
                        doc = frappe.new_doc("Batch")
                        doc.item = d.item_code
                        doc.insert(ignore_permissions=1)
                        d.batch_no = doc.name
        else:
            for d in self.items:
                if not d.batch_no:
                    frappe.throw(_("Row {0}, Batch No must be set.").format(d.idx))

    def on_submit(self):
        super(StockReconciliationGP, self).on_submit()
        self.update_work_order_revised_qty()

    def on_cancel(self):
        self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Repost Item Valuation")
        self.make_sle_on_cancel()
        self.make_gl_entries_on_cancel()
        self.repost_future_sle_and_gle()
        if self.purpose == "Opening Stock":
            self.delete_auto_created_batches()
        self.reset_foms_sync()

    def update_work_order_revised_qty(self):
        if self.purpose != "Stock Reconciliation":
            return
        for d in self.get("items"):
            res = frappe.db.sql("""
                SELECT ste.work_order, ste.name AS stock_entry, ste_item.item_code, ste_item.batch_no, ste.posting_date
                FROM `tabStock Entry Detail` ste_item
                JOIN `tabStock Entry` ste ON ste.name = ste_item.parent
                WHERE ste_item.batch_no = %s AND ste.docstatus = 1
            """, (d.batch_no), as_dict=1)
            if res:
                wo = res[0].work_order
                frappe.db.set_value("Work Order", wo, "revised_qty", d.qty)

    def reset_foms_sync(self):
        old_doc = self.get_doc_before_save()
        if old_doc and old_doc.docstatus == 1 and self.docstatus == 2:
            for d in self.get("items"):
                d.db_set("foms_sync", 0)
