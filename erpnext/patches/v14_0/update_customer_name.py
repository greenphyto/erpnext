import frappe

def execute():
    update_system_settings()
    delete_existing_property_setters()
    update_existing_customer()

def update_system_settings():
    frappe.db.set_value("Selling Settings", "Selling Settings", "cust_master_name", "Naming Series")
    frappe.db.set_value("Buying Settings", "Buying Settings", "supp_master_name", "Naming Series")

def delete_existing_property_setters():
    frappe.delete_doc("Property Setter", "Customer-naming_series-options", ignore_missing=True)
    frappe.delete_doc("Property Setter", "Supplier-naming_series-options", ignore_missing=True)

def update_existing_customer():
    pass