import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, get_last_day

from erpnext.accounts.doctype.budget.budget import Budget


class BudgetGP(Budget):
    def validate(self):
        if not self.get(frappe.scrub(self.budget_against)):
            frappe.throw(_("{0} is mandatory").format(self.budget_against))
        if self.accounts:
            self.validate_duplicate()
            self.validate_accounts()
            self.calculate_total_budget_amount()
            self.set_null_value()
            self.validate_applicable_for()
        else:
            if self.docstatus == 1:
                frappe.throw(_("At least one budget account is required to submit the document"))

    def calculate_total_budget_amount(self):
        month_name = ["january", "february", "march", "april", "may", "june",
                      "july", "august", "september", "october", "november", "december"]
        for d in self.get("accounts"):
            d.budget_amount = 0
            for month in month_name:
                d.budget_amount += flt(d.get(month, 0))
