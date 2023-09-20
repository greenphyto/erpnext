import frappe

def execute():
    update_reff_dn_si()

def update_reff_dn_si():
    data = frappe.get_all("Delivery Note", {"docstatus":1})
    for d in data:
        doc = frappe.get_doc("Delivery Note", d.name)
        doc.update_reference_si()
        print("Update dn {}".format(d.name))