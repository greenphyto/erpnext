import frappe
from frappe import _
from frappe.utils import flt

from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt


class PurchaseReceiptGP(PurchaseReceipt):
    def link_internal_company(self):
        if not self.is_internal_supplier:
            return
        po_number = next((d.purchase_order for d in self.items if d.purchase_order), None)
        if not po_number:
            return
        inter_so_name = frappe.get_value("Purchase Order", po_number, "inter_company_order_reference")
        if not inter_so_name:
            inter_so_name = frappe.db.get_value(
                "Sales Order",
                {"inter_company_order_reference": po_number, "docstatus": 1},
                "name",
            )
            if not inter_so_name:
                return
            frappe.db.set_value("Purchase Order", po_number, "inter_company_order_reference", inter_so_name)
        represents_company = frappe.get_value("Purchase Order", po_number, "represents_company")
        inter_dn_number = frappe.db.sql("""
            SELECT DISTINCT dni.parent
            FROM `tabDelivery Note Item` dni
            JOIN `tabDelivery Note` dn ON dn.name = dni.parent
            WHERE dn.docstatus = 1 AND dni.against_sales_order = %s
            ORDER BY dn.creation DESC LIMIT 1
        """, (inter_so_name), as_dict=False)
        if not inter_dn_number:
            return
        inter_dn_number = inter_dn_number[0][0]
        if inter_dn_number:
            frappe.db.set_value("Delivery Note", inter_dn_number, "inter_company_reference", self.name)
        self.inter_company_reference = inter_dn_number
        self.represents_company = represents_company

    def validate_delivery_note_internal_sent(self):
        if not self.is_internal_supplier:
            return
        make_strict = frappe.db.get_single_value("Buying Settings", "forbidden_pr_before_dn")
        if not make_strict:
            return
        if not self.inter_company_reference:
            frappe.throw(_("Cannot create Purchase Receipt before Delivery Note is sent. <br>Please contact {} for more information.".format(self.supplier)))

    def update_bom_rate(self):
        if not frappe.db.get_single_value("Manufacturing Settings", "update_bom_rate_as_pr_price"):
            return
        item_list = []
        for d in self.get("items"):
            key = d.item_code
            if key not in item_list:
                item_list.append(key)
        _update_BOM_rate(item_list)


def _update_BOM_rate(item_list):
    bom_list = frappe.db.sql("""
        SELECT i.item_code, b.name, i.uom, i.qty, i.rate
        FROM `tabBOM Item` i
        LEFT JOIN `tabBOM` b ON b.name = i.parent
        WHERE b.is_active = 1 AND b.is_default = 1
            AND b.docstatus = 1
            AND i.item_code IN %(item_list)s
        GROUP BY b.name
    """, {"item_list": item_list}, as_dict=1, debug=0)
    for b in bom_list:
        bom = frappe.get_doc("BOM", b.name)
        bom.rm_cost_as_per = "Last Purchase Rate"
        bom.update_cost(update_parent=True, from_child_bom=False, update_hour_rate=False, save=True)
        bom.save()
