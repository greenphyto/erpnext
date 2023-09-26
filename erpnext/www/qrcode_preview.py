import frappe

def get_context(context):
    args = frappe.form_dict
    doctype = args.get("doctype")
    name = args.get("name")
    if frappe.session.user == "Guest":
        print("here 8")
        return
    
    if not doctype or not name:
        return
    
    if not frappe.db.exists(doctype, name):
        return
    
    context.doc = frappe.get_doc(doctype, name)