import frappe
from erpnext.controllers.foms import get_workstation_name,create_workstation_process
"""
bench --site test3 execute erpnext.patches.v14_0.fix_manufacturing.add_workstation
"""

def execute():
    update_bom_to_against_job_card()
    update_valuation_rate()
    update_enable_batch_no()

def execute2():
    add_workstation()
    update_bom()


def update_bom_to_against_job_card():
    frappe.db.sql("""
        UPDATE `tabBOM` 
        SET 
            transfer_material_against = 'Job Card'
        WHERE
            transfer_material_against = 'Work Order'           
    """)
    
def update_valuation_rate():
    frappe.db.sql("""
        UPDATE `tabItem` 
            SET 
                valuation_rate = 1
            WHERE
                valuation_rate = 0
    """)

def update_enable_batch_no():
    frappe.db.sql("""
        UPDATE `tabItem` 
        SET 
            has_batch_no = 1,
            create_new_batch = 1,
            batch_number_series = CONCAT(item_code, "BN.#####"),
            has_expiry_date=1,
            shelf_life_in_days=365
        WHERE
            is_stock_item = 1 and (foms_raw_id is not null or foms_product_id is not null)
    """)

def add_workstation():
    # update item wk
    data = frappe.db.sql('select name,item from `tabBOM` where docstatus = 1 and is_default = 1 group by item', as_dict=1)
    for d in data:
        create_workstation_process(d.item)
        print(d)

def update_bom():
    data = frappe.db.sql('select name,item from `tabBOM` where docstatus = 1 and is_default = 1 group by item', as_dict=1)
    for d in data:
        doc = frappe.get_doc("BOM", d.name)
        doc.db_set("docstatus", 0)
        for op in doc.operations:
            wk = get_workstation_name(doc.item, op.operation)
            print(wk)
            op.workstation = wk
        doc.save()
        doc.submit()
        print(49, d)



