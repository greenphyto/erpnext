import frappe
from frappe import _
from frappe.utils import cint

from erpnext.buying.doctype.buying_settings.buying_settings import BuyingSettings


class BuyingSettingsGP(BuyingSettings):
    @frappe.whitelist()
    def update_supplier_account(self, series_filter=None, mode="Only if not set"):
        for d in self.get("default_supplier_account"):
            series = d.code.replace("...", "")
            if series_filter and series not in series_filter:
                continue
            suppliers = frappe.db.get_all("Supplier", {"supplier_code": ["like", series + "%"]})
            for sup in suppliers:
                doc = frappe.get_doc("Supplier", sup.name)
                has_company = False
                for row in doc.get("accounts"):
                    if row.company == d.company:
                        has_company = True
                        if mode == "Replace all":
                            row.account = d.account
                        break

                if not has_company:
                    row = doc.append("accounts")
                    row.account = d.account
                    row.company = d.company

                doc.save()


def get_series_pr_required(series):
    res = frappe.get_value(
        "Series PO required PR",
        {"series": series, "parent": "Buying Settings", "parentfield": "series_required_pr"},
        "require_pr",
    )

    return cint(res)
