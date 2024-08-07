import frappe

def execute():
    update_bom_to_against_job_card()
    update_valuation_rate()

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