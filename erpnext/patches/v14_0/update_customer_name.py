import frappe

def execute():
    update_system_settings()
    delete_existing_property_setters()
    update_existing_customer()
    update_existing_supplier()

def update_system_settings():
    frappe.db.set_value("Selling Settings", "Selling Settings", "cust_master_name", "Naming Series")
    frappe.db.set_value("Buying Settings", "Buying Settings", "supp_master_name", "Naming Series")

def delete_existing_property_setters():
    frappe.delete_doc("Property Setter", "Customer-naming_series-options", ignore_missing=True)
    frappe.delete_doc("Property Setter", "Supplier-naming_series-options", ignore_missing=True)

from frappe import rename_doc
def update_existing_customer():
    _update_existing_data("Customer")

def update_existing_supplier():
    _update_existing_data("Supplier")

def _update_existing_data(doctype):
    data = frappe.db.get_list(doctype, {"name":['not like', '%%C00%%']})
    print("Total {} {} to be rename".format(len(data), doctype))
    for d in data:
        doc = frappe.get_doc(doctype, d.name)
        old_name = str(doc.name)
        if doctype == "Customer":
            doc.naming_series = "C.#####"
        else:
            doc.naming_series = "S.#####"

        doc.autoname()
        new_name = doc.name
        print("Rename {} {} to {}".format(doctype, d.name, new_name))
        rename_doc(doctype, old_name, new_name)