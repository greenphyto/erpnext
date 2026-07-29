import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder


class PurchaseOrderGP(PurchaseOrder):
    def validate(self):
        super(PurchaseOrderGP, self).validate()
        self.validate_item_non_stock()

    def on_submit(self):
        super(PurchaseOrderGP, self).on_submit()
        self.update_material_request()

    def validate_item_non_stock(self):
        pass

    def update_material_request(self):
        mr_list = []
        for d in self.get("items"):
            if d.material_request and d.material_request not in mr_list:
                mr_list.append(d.material_request)

        for d in mr_list:
            po_list = []
            po_exists = frappe.db.get_value("Material Request", d, "purchase_order") or ""
            for x in po_exists.split(","):
                if cstr(x):
                    po_list.append(cstr(x).strip())
            if self.name not in po_list:
                po_list.append(self.name)
            list_view = ", ".join(po_list)
            if list_view != po_exists:
                frappe.db.set_value("Material Request", d, "purchase_order", list_view)


@frappe.whitelist()
def get_internal_supplier_currency(supplier):
    if not supplier:
        return None
    company = frappe.get_value("Supplier", supplier, "represents_company")
    if not company:
        return None
    currency = frappe.get_value("Company", company, "default_currency")
    return currency
