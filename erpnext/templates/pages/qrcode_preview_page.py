import frappe

def get_context(context):
    args = frappe.form_dict
    doctype = args.get("cdt")
    name = args.get("cdn")
    if not doctype or not name:
        return
    
    if not frappe.db.exists(doctype, name):
        return
    
    doc = frappe.db.get_value(doctype, name, "*")
    doc.doctype = doctype
    context.doc = doc
    context.name = name
    context.doctype = doctype
    context.cdt = frappe.form_dict.get("cdt")
    context.cdn =  frappe.form_dict.get("cdn")

    name_view = (doc.asset_name)[:75]
    name_view_length = len(name_view)
    font_size = 36
    if name_view_length < 12:
        font_size = 56
    elif name_view_length < 24:
        font_size = 40
    elif name_view_length < 40:
        font_size = 36
    elif name_view_length < 60:
        font_size = 28
    else:
        font_size = 24
        name_view += "..."
    
    context.name_view = name_view
    context.font_size = font_size

    