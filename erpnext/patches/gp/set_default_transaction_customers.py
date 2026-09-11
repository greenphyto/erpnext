import frappe


CUSTOMER_FIELDS = {
    "donor_customer": "Donor",
    "production_customer": "Production",
    "marketing_customer": "Marketing",
    "internal_staff_customer": "Internal Staff",
}


def execute():
    customers = {
        fieldname: customer
        for fieldname, customer in CUSTOMER_FIELDS.items()
        if frappe.db.exists("Customer", customer)
    }

    if not customers:
        return

    for company in frappe.get_all("Company", pluck="name"):
        for fieldname, customer in customers.items():
            if not frappe.db.get_value("Company", company, fieldname):
                frappe.db.set_value("Company", company, fieldname, customer, update_modified=False)
