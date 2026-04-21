import frappe

# bench --site test5 execute erpnext.patches.v14_0.add_donor_customer.execute
def execute():
    add_donor_customer()
    copy_donation_address()

def add_donor_customer():
    if not frappe.db.exists("Customer", "Donor"):
        doc = frappe.new_doc("Customer")
        doc.customer_name = "Donor"
        doc.customer_type = "Individual"
        doc.customer_group = "Non Profit"
        doc.is_group = 0
        doc.territory = "All Territories"
        doc.save(ignore_permissions=True)
        print("Created 'Donor' customer")

def copy_donation_address():
    # copy donation address to donor
    all_address = frappe.db.sql("""
        SELECT 
            a.name
        FROM
            `tabAddress` a
                LEFT JOIN
            `tabDynamic Link` dl ON a.name = dl.parent
        WHERE
            dl.link_doctype = 'Customer'
                AND dl.link_name = 'Donation'
    """, as_dict=1)

    for address in all_address:
        doc = frappe.get_doc("Address", address.name)
        skip_add = False
        for d in doc.get("links"):
            if d.link_name == "Donor":
                skip_add = True
        
        if not skip_add:
            row = doc.append("links")
            row.link_doctype = "Customer"
            row.link_name = "Donor"
            row.link_title = "Donor"
            print(f"Linking address {address.name} to Donor customer")
            doc.save(ignore_permissions=True)   