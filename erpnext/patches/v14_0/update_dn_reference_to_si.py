import frappe

"""
bench --site mysite.localhost execute erpnext.patches.v14_0.update_dn_reference_to_si.execute
"""

def execute():
    update_reff_dn_si()
    update_reff_si_dn()

def update_reff_dn_si():
    data = frappe.get_all("Delivery Note", {"docstatus":1})
    for d in data:
        doc = frappe.get_doc("Delivery Note", d.name)
        doc.set_other_reff()
        doc.db_update_all()
        print("Update DN {}".format(d.name))

def update_reff_si_dn():
    data = frappe.get_all("Sales Invoice", {"docstatus":1})
    for d in data:
        doc = frappe.get_doc("Sales Invoice", d.name)
        doc.set_other_reff()
        doc.db_update_all()
        print("Update SI {}".format(d.name))