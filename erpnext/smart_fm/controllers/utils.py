import frappe
from frappe.utils import cint, getdate

def get_day_diff(date1, date2):
    delta = getdate(date2) - getdate(date1)
    return delta.days