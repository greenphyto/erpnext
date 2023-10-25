import frappe

def execute():
    frappe.db.sql("""
        update tabToDo set status="Planned" where status = "Open"
    """)

    frappe.db.sql("""
        update tabToDo set status="Closed" where status = "Completed"
    """)