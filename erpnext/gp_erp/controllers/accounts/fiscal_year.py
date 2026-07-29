import frappe
from frappe import _

from erpnext.accounts.doctype.fiscal_year.fiscal_year import FiscalYear


class FiscalYearGP(FiscalYear):
    def validate(self):
        super(FiscalYearGP, self).validate()
        self.add_company_default()

    def add_company_default(self):
        if self.get("companies"):
            return
        company_list = frappe.db.get_all("Company")
        for c in company_list:
            company = c['name']
            add = True
            for d in self.get("companies"):
                if d.company == company:
                    add = False
                    break
            if add:
                row = self.append("companies")
                row.company = company
