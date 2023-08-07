import frappe
from frappe.utils import getdate, cint, get_url
import json
from frappe.twofactor import get_qr_svg_code

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
def create_todo(doc, method=""):
	task = ""
	if doc.doctype == "Asset Maintenance Log":
		task = doc.task_name
	elif doc.doctype == "Asset Repair":
		task = doc.description[:150]

	return frappe.get_doc(
		{
			"doctype": "ToDo",
			"description": task,
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


@frappe.whitelist()
def get_qcode(data={}, doctype=None, docname=None, get_link=False):
	# to generate qr code and store to QRCode Data
	# return base64 string images
	if not data and not doctype and not docname:
		return ""
	
	def get_link_detail(doc_name):
		ids = frappe.generate_hash(length=8)
		params = "qr={}&id={}".format(doc_name, ids)
		link = get_url("/api/method/erpnext.smart_fm.api.qrcode?{}".format(params))
		return link

	result_name = ""
	if data:
		# find exists
		data_temp = json.dumps(data, sort_keys=True)
		exists = frappe.db.exists("QRCode Data", {"data":data_temp})
		if exists:
			result_name = exists
		else:
			doc = frappe.new_doc("QRCode Data")
			doc.data = data
			doc.insert(ignore_permissions=True)
			result_name = doc.name

	elif doctype and docname:
		exists = frappe.db.exists("QRCode Data", {"doc_type":doctype, "doc_name":docname})
		if exists:
			result_name = exists
		else:
			doc = frappe.new_doc("QRCode Data")
			doc.doc_type = doctype
			doc.doc_name = docname
			doc.insert(ignore_permissions=True)
			result_name = doc.name
	else:
		return ""
	
	link = get_link_detail(result_name)
	if get_link:
		return link
	
	# get base 64 string images
	img_string = get_qr_svg_code(link)
	return img_string			
