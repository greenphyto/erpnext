import frappe
from frappe.utils import getdate

"""
Only be matching with listed company and the domain.
if this domain has in company list, so the employee is based on company listed.
Mus be set:
 - add role "Vendor" by default
 - Field Domain in Company
"""
def give_role_based_on_email_domain(doc, method=""):
    email_domain = doc.email.split("@")[-1]
    # find exists domain company
    company = frappe.db.exists("Company", {"domain": email_domain})

    if not company:
        doc.add_roles("Vendor")
    else:
        # also create employee
        create_employee_from_user(doc, company)

        doc.reload()
        doc.add_roles("Employee")

def create_employee_from_user(doc, company):
    if frappe.db.exists("Employee", {"user_id": doc.name}):
        return

    emp = frappe.new_doc("Employee")
    emp.user_id = doc.email
    emp.full_name = doc.full_name
    emp.first_name = doc.first_name
    emp.last_name = doc.last_name
    emp.date_of_joining = getdate()
    emp.date_of_birth = getdate("2000-01-01")
    emp.gender = "Male"

    emp.company = company
    emp.save(ignore_permissions=True)

"""
Need to add additional reference name on ToDo, which is generated from Assets Maintenance Log.
The Reference is used by list view to get valid link to directed
"""     
def add_assets_maintenance_log_name(doc, method=""):
    if doc.reference_type == "Asset Maintenance":
        reff_name = frappe.get_value("Asset Maintenance Log", {
            "asset_maintenance":doc.reference_name,
            "task_name": doc.description
        }, order_by="creation desc")
        if reff_name:
            print(reff_name)
            doc.additional_reference = reff_name


