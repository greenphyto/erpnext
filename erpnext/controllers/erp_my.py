import frappe, json
from frappe.utils import cint, flt, getdate, cstr, safe_abs, add_months, add_days
from six import string_types

"""
ERP Controller specific to Malaysia Company
"""

COMPANY = "Greenphyto Tech Sdn Bhd"

def overide_exp_date_grn(doc, method=""):
    # increase 2 weeks
    DAYS_ADD = 14
    if doc.doctype == "Purchase Receipt" and doc.company == COMPANY:
        for item in doc.items:
            if item.batch_no:
                exp_date = frappe.db.get_value("Batch", item.batch_no, "expiry_date")
                new_date = getdate(add_days(exp_date, DAYS_ADD))
                frappe.db.set_value("Batch", item.batch_no, "expiry_date", new_date)