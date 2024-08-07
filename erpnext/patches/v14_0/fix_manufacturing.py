import frappe

def execute():
    update_bom_to_against_job_card()
    update_valuation_rate()
    update_enable_batch_no()

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