import frappe
from frappe.core.page.permission_manager.permission_manager import reset
def execute():
    cdt_list = ['Tenant Feedback', 'Vendor Registration', 'Key Control', 'Visitor Registration', 'Emergency Contact Information']
    for cdt in cdt_list:
        reset(cdt)
    
