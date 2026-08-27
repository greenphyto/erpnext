import frappe

# erpnext.patches.v14_0.add_mixing_operation
def execute():
    opr = ['Mixing', 'Mixing Process']
    for d in opr:
        exists = frappe.db.exists("Operation", d)
        if not exists:
            doc = frappe.new_doc("Operation")
            doc.__newname = d
            doc.save()
            print("Creating new operation ", d)
