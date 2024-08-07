import frappe

def execute():
    update_bom_to_against_job_card()

def update_bom_to_against_job_card():
    frappe.db.sql("""
        UPDATE `tabBOM` 
        SET 
            transfer_material_against = 'Job Card'
        WHERE
            transfer_material_against = 'Work Order'           
    """)
