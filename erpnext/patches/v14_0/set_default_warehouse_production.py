import frappe

# erpnext.patches.v14_0.set_default_warehouse_production
def execute():
    doc = frappe.get_doc("Manufacturing Settings")
    doc.default_source_warehouse = ""
    doc.default_fg_warehouse = 'Finished Goods - GPL'
    doc.default_wip_warehouse = 'Work In Progress - GPL'
    doc.backflush_raw_materials_based_on = 'Material Transferred for Manufacture'
    doc.allow_single_completed_work_order = ""
    doc.update_bom_rate_as_pr_price = 1
    doc.overproduction_percentage_for_work_order = 0
    doc.overproduction_percentage_for_sales_order = 0
    print("Update Manfaucturing Settings")