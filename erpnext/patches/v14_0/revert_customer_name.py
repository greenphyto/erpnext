import frappe

def execute():
    update_system_settings()
    update_existing_customer()
    update_existing_supplier()
    frappe.db.commit()

def update_system_settings():
    doc = frappe.get_single("Selling Settings")
    doc.cust_master_name = "Customer Name"
    doc.save()

    doc = frappe.get_single("Buying Settings")
    doc.supp_master_name = "Supplier Name"
    doc.save()
    
from frappe import rename_doc
def update_existing_customer():
    _update_existing_data("Customer")

def update_existing_supplier():
    _update_existing_data("Supplier")

def _update_existing_data(doctype):
    data = frappe.db.sql("""
        select name, creation from `tab{}` c where c.name != c.{}_name
        order by creation asc
    """.format(doctype, frappe.scrub(doctype)), as_dict=1)

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
        print("Rename {} {} to {}, {}".format(doctype, d.name, new_name, d.creation))
        rename_doc(doctype, old_name, new_name)