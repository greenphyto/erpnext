import frappe
def execute():
    add_company_admin()

def add_company_admin():
    # iterate through all companies and ensure they have an admin user set
    for company in frappe.get_all("Company", pluck="name"):
        # if admin_user field is already populated skip
        if frappe.db.get_value("Company", company, "admin_user"):
            continue

        # determine series abbreviation for email template (fallback to first
        # two letters of company if not set)
        abbr = frappe.get_value("Company", company, "series_abbr") or "SG"
        email = f"admin_{abbr}@example.com"
        full_name = f"Company Admin {abbr}"

        # create the user document without sending a welcome email
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "full_name": full_name,
        })
        # lock the user to the company and prevent company switch
        user.company = company
        user.cannot_change_company = 1
        user.company_selected = company
        user.send_welcome_email = 0

        user.insert(ignore_permissions=True)

        # assign every active role to the new company admin
        roles = frappe.db.get_all("Role", {"disabled": 0}, pluck="name")
        user.add_roles(*roles)
        user.save()

        # update the company record with the created user
        frappe.db.set_value("Company", company, "admin_user", user.name)
