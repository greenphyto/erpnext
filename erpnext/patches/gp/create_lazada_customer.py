import frappe


def execute():
    company = "Greenphyto Pte Ltd"
    create_lazada_customer(company)
    create_lazada_warehouse(company)


def create_lazada_customer(company):
    if frappe.db.exists("Customer", "Lazada"):
        return

    customer = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": "Lazada",
        "customer_type": "Company",
        "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups",
        "territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
        "company": company,
    })
    customer.insert(ignore_permissions=True)

    address = frappe.get_doc({
        "doctype": "Address",
        "address_title": "Lazada",
        "address_type": "Billing",
        "address_line1": "79 Anson Road",
        "city": "Singapore",
        "country": "Singapore",
        "pincode": "079906",
        "is_primary_address": 1,
        "links": [{
            "link_doctype": "Customer",
            "link_name": "Lazada",
        }],
    })
    address.insert(ignore_permissions=True)

    frappe.db.set_value("Customer", "Lazada", "website", "https://www.lazada.com")
    frappe.db.set_single_value("Lazada Settings", "lazada_customer", customer.name)
    frappe.db.commit()


def create_lazada_warehouse(company):
    warehouse_name = "Lazada Warehouse - GPL"
    parent_warehouse = "All Warehouses - GPL"

    if frappe.db.exists("Warehouse", warehouse_name):
        frappe.db.set_single_value("Lazada Settings", "default_warehouse", warehouse_name)
        frappe.db.commit()
        return

    wh = frappe.get_doc({
        "doctype": "Warehouse",
        "warehouse_name": "Lazada Warehouse",
        "company": company,
        "is_group": 0,
        "parent_warehouse": parent_warehouse,
    })
    wh.insert(ignore_permissions=True)

    frappe.db.set_single_value("Lazada Settings", "default_warehouse", wh.name)
    frappe.db.commit()
