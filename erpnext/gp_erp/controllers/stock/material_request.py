import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.stock.doctype.material_request.material_request import MaterialRequest


class MaterialRequestGP(MaterialRequest):
    def set_is_low_amount(self):
        raw_material_totals, general_item_totals = 0, 0
        for d in self.get("items"):
            if "Raw Material" in d.item_group or "Raw Material" == d.item_group:
                raw_material_totals += flt(d.base_net_amount)
            else:
                general_item_totals += flt(d.base_net_amount)
        forbidden = []
        if flt(raw_material_totals) < 5001:
            forbidden.append(False)
        else:
            forbidden.append(True)
        if flt(general_item_totals) < 1001:
            forbidden.append(False)
        else:
            forbidden.append(True)
        if not any(forbidden):
            self.is_low_amount = 1
            return 1
        else:
            self.is_low_amount = 0
            return 0

    def check_attachment(self):
        if self.is_new() or self.flags.ignore_mandatory:
            return
        attachments = frappe.get_all(
            "File",
            fields=["name", "file_name", "file_url", "is_private"],
            filters={"attached_to_name": self.name, "attached_to_doctype": self.doctype},
        )
        if len(attachments) == 0:
            frappe.throw(_("Unable to approve due to missing attachment"))
        self.set_status(update=True)

    def set_expense_code(self):
        stock_expense = frappe.get_value("Company", self.company, "stock_received_but_not_billed")
        for d in self.get("items"):
            if frappe.get_value("Item", d.item_code, 'is_stock_item'):
                d.expense_account = stock_expense
