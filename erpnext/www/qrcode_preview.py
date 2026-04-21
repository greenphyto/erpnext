import frappe

def get_context(context):
    args = frappe.form_dict
    doctype = args.get("doctype")
    name = args.get("name")
    
    if not doctype or not name:
        return
    
    if not frappe.db.exists(doctype, name):
        return
    
    context.doc = frappe.get_doc(doctype, name)
    context.font_size = "2.3em"
    if len(context.doc.asset_name) > 20:
        context.font_size = "1.9em"
    if len(context.doc.asset_name) > 40:
        context.font_size = "1.5em"
    if len(context.doc.asset_name) > 60:
        context.font_size = "1em"