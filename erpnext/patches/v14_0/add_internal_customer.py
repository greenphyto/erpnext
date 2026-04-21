
import frappe

def execute():
    exist = frappe.get_value("Customer", "Internal Customer")
    if exist:
        return
    
    doc = frappe.new_doc("Customer")
    doc.customer_name = "Internal Customer"
    doc.customer_group = "All Customer Groups"
    doc.territory = "Singapore"
    doc.insert(ignore_permissions=1)
    print("Done add new internal customer")