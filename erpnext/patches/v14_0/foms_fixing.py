import frappe, json
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

"""
bench --site test4 execute erpnext.patches.v14_0.foms_fixing.fix_raw_material_name
"""
def fix_raw_material_name():
    # renew item name based on log
    logs = frappe.db.get_all("FOMS Data Mapping", {"data_type":"Raw Material"}, ['raw_data', 'doc_name'])
    # if item name not match, renew
    for log in logs:
        data = json.loads(log.raw_data)
        item_name = frappe.get_value("Item", log.doc_name, "item_name")
        if data.get('rawMaterialName') and item_name != data['rawMaterialName']:
            print("rename", log['doc_name'], "to", data['rawMaterialName'])
            frappe.db.set_value("Item", log['doc_name'], "item_name", data['rawMaterialName'])

"""
bench --site test3 execute erpnext.patches.v14_0.foms_fixing.refetch_item_name
"""
def refetch_item_name(item_code=""):
    # BOM
    # Work Order
    table_name = {
        "BOM":["BOM Item"],
        "Work Order":["Work Order Item"],
        "Sales Order":["Sales Order Item"],
        "Sales Invoice":["Sales Invoice Item"],
        "Delivery Note":["Delivery Note Item"],
        "Purchase Order":["Purchase Order Item"],
        "Purchase Invoice":["Purchase Invoice Item"],
        "Purchase Receipt":["Purchase Receipt Item"],
        "Material Request":["Material Request Item"],
    }

    cond = ""
    if item_code:
        cond = "and b.item_code = %(item_code)s"

    for key, val in table_name.items():
        for table in val:
            print("Update to ", table)
            frappe.db.sql("""
            UPDATE `tab{}` b
                    LEFT JOIN
                `tabItem` i ON i.name = b.item_code 
            SET 
                b.item_name = i.item_name 
            WHERE 
                b.item_code is not null 
                {}
            """.format(table, cond), {"item_code":item_code}, debug=1)