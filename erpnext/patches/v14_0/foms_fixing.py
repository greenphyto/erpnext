import frappe
from erpnext.controllers.foms import (
	get_raw_material, create_raw_material, get_products, get_recipe,create_foms_data,
	create_bom_products, get_work_order, create_work_order,get_bom_for_work_order
)

"""
bench --site test4 execute erpnext.patches.v14_0.foms_fixing.re_sync_foms_work_order
"""
def re_sync_foms_work_order():
    # delete all which not have lot id
    # for d in frappe.db.get_all("Work Order", {"docstatus":0}):
    #     frappe.delete_doc("Work Order", d.name)
    #     print("Delete ", d.name)

    frappe.db.sql("delete from `tabWork Order` where docstatus = 0")

    # resync
    get_work_order()