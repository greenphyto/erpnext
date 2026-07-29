import frappe
from frappe import _
from frappe.utils import cint

from erpnext.buying.doctype.buying_settings.buying_settings import BuyingSettings


class BuyingSettingsGP(BuyingSettings):
    @frappe.whitelist()
    def update_supplier_account(self):
        for d in self.get("default_supplier_account"):
            series = d.code.replace("...", "")
            suppliers = frappe.db.get_all("Supplier", {"supplier_code": ["like", series + "%"]})
            for sup in suppliers:
                doc = frappe.get_doc("Supplier", sup.name)
                change = False
                for row in doc.get("accounts"):
                    if row.company == d.company:
                        row.account = d.account
                        change = True
                if not change:
                    row = doc.append("accounts")
                    row.account = d.account
                    row.company = d.company
                doc.save()
