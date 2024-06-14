import frappe

"""
bench --site test4 execute erpnext.patches.v14_0.foms_pacthes.delete_all_item
"""
def delete_all_item():
    def _delete(name):
        try:
            log = frappe.db.exists("FOMS Data Mapping", {"doc_type":"Item", "doc_name":name} )
            if log:
                print("Delete ", d.name)
                frappe.delete_doc("FOMS Data Mapping", log)
                frappe.delete_doc("Item", name)
        except Exception as e:
            print("Skip ",name, e)

    for d in frappe.get_all("Item"):
        _delete(d.name)

"""
bench --site test4 execute erpnext.patches.v14_0.foms_pacthes.delete_all_bom
"""
def delete_all_bom():
    for d in frappe.db.get_all("FOMS Data Mapping", {"doc_type":"BOM", "doc_name":['is', 'set']}, ['name', 'doc_name']):
        if frappe.db.exists("BOM", d.doc_name):
            print("Delete", d.doc_name)
            frappe.delete_doc("BOM", d.doc_name)
        else:
            frappe.delete_doc("FOMS Data Mapping", d.name)