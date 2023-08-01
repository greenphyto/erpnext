import frappe
from frappe.utils import getdate, cint

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
    if doc.reference_type == "Asset Maintenance" and not doc.additional_reference:
        reff_name = frappe.get_value("Asset Maintenance Log", {
            "asset_maintenance":doc.reference_name,
            "task_name": doc.description
        }, order_by="creation desc")
        if reff_name:
            print(reff_name)
            doc.additional_reference = reff_name

"""
Create ToDo if Asset Maintenance Log created
"""
def create_todo_from_maintenance_log(doc, method=""):
    return frappe.get_doc(
		{
			"doctype": "ToDo",
			"description": doc.task_name,
            "reference_type": doc.doctype,
            "reference_name": doc.name,
            "assigned_by": frappe.session.user
		}
	).insert(ignore_permissions=True)

"""
- Find doc with -1 H, today, and due date Task
- Specially to Smart FM's Doctype
"""
# run_notifications
def send_due_date_notification_task():
    if not cint(frappe.db.get_single_value("Smart FM Settings", "enable_daily_task_notification")):
        return
    
    method = "reminder_task_notification"

    # get list todo
    data = frappe.db.sql("""
        SELECT 
            name, date, reminder_at, DATEDIFF(date, CURDATE()) as left_days
        FROM
            `tabToDo`
        WHERE
            status = 'Open' and DATEDIFF(date, CURDATE()) <= reminder_at
    """, as_dict=1)
    for d in data:
        doc = frappe.get_doc("ToDo", d.name)
        doc.run_notifications(method)

