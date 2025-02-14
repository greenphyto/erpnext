import frappe

def execute():
    role = frappe.get_doc({
        "role_name":"Visit Manager",
        "doctype":"Role"
    }).save()