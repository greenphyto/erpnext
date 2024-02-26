import frappe

"""
bench --site test1 execute erpnext.patches.vgp.update_is_mirror_check.update_is_mirror
"""
def update_is_mirror():
    maps = frappe.db.get_list("Sync Map", {"destination_doctype":"Asset"}, "destination_name")
    for d in maps:
        name = d.destination_name
        print(name)
        frappe.db.set_value("Asset", name, "is_mirroring", 1)