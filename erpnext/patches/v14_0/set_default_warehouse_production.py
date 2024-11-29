import frappe

# erpnext.patches.v14_0.set_default_warehouse_production
def execute():
    doc = frappe.get_doc("Manufacturing Settings")
    doc.default_source_warehouse = ""
    doc.default_fg_warehouse = 'Finished Goods - GPL'
    doc.default_wip_warehouse = 'Work In Progress - GPL'
    print("Update Manfaucturing Settings")