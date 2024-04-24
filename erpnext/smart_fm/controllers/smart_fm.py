import frappe
from frappe.utils import getdate, cint, get_url, cstr, now
import json
from frappe import _
from erpnext.smart_fm.controllers.utils import get_qr_svg_code
from frappe.permissions import (
	add_user_permission,
	has_permission,
	remove_user_permission,
)


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
			doc.additional_reference = reff_name

def validate_asset_repair_description(doc, method=""):
	if not doc.description and not doc.get("request_id"):
		frappe.throw(_("Description must be set!"))

	if doc.get("request_id"):
		desc = frappe.get_value("Maintenance Request", doc.get("request_id"), "description")
		doc.description = desc

"""
Create ToDo if Asset Maintenance Log created
"""
def create_todo(doc, method=""):
	task = ""
	due_date = now()
	if doc.doctype == "Asset Maintenance Log":
		task = doc.task_name
		due_date = doc.due_date
		if not task:
			frappe.throw(_("Task is missing!"))
			
	elif doc.doctype == "Asset Repair":
		due_date = doc.due_date
		if doc.get("description"):
			task = doc.description[:150]

	return frappe.get_doc(
		{
			"doctype": "ToDo",
			"description": task,
			"reference_type": doc.doctype,
			"reference_name": doc.name,
			"assigned_by": frappe.session.user,
			"date":due_date
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
			status = 'Planned' and DATEDIFF(date, CURDATE()) <= reminder_at
			and reminder_off = 0
	""", as_dict=1)
	for d in data:
		doc = frappe.get_doc("ToDo", d.name)
		doc.run_notifications(method)


@frappe.whitelist()
def get_qrcode(data={}, doctype=None, docname=None, get_link=False, commit=False):
	# to generate qr code and store to QRCode Data
	# return base64 string images
	if not data and not doctype and not docname:
		return ''
	
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

	if commit:
		frappe.db.commit()
	
	# get base 64 string images
	img_string = get_qr_svg_code(link)
	return cstr(img_string)	

def create_asset_qrcode(doc, method=""):
	if not doc.qrcode_image:
		url = save_qrcode_image(doc.doctype, doc.name, 1)
		doc.qrcode_image = url

import imgkit,base64
def save_qrcode_image(doctype, name, update_db=False):
	# get image qrcode
	# save to doctype
	if not frappe.db.exists(doctype, name):
		return
	
	url = get_url("/qrcode/{}/{}".format(doctype, name))
	options = {'width': 400, 'disable-smart-width': ''}
	string_img = imgkit.from_url(url, False, options=options)
	encoded = base64.b64encode(string_img)

	# save file
	filenme= "QR Code - {} - {}.png".format(doctype, name)
	content = encoded
	is_private = 0
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filenme,
			"attached_to_doctype": doctype,
			"attached_to_name": name,
			"content": content,
			"decode": True,
			"is_private": is_private,
		}
	)
	file.save(ignore_permissions=True)
	file_url = file.file_url

	if doctype in ['Asset']:
		if update_db:
			frappe.db.set_value(doctype, name, "qrcode_image", file_url, update_modified=False)			

	return file_url

def close_todo(doc, method=""):
	close = False
	conplete_status_list = {
		"Tenant Feedback": "Resolved",
		"Inspection Checklist":"Resolved",
		"Emergency Contact Flow":"Resolved",
		"Key Control":"Resolved",
		"Accident or Incident Report Flow":"Resolved",
		"Access Request Flow":"Resolved",
		"Maintenance Request":"Resolved",
		"Vendor Registration": "Resolved",
		"Smart FM Work Order": "Resolved",
		"Asset Maintenance Log": "Completed",
		"Asset Repair": "Completed",
	}
	if doc.doctype not in conplete_status_list:
		return
	
	status = doc.get("workflow_state") or doc.get("status")
	if doc.doctype == "Asset Maintenance Log":
		status = doc.maintenance_status
	if doc.doctype == "Asset Repair":
		status = doc.repair_status
	
	if doc.docstatus == 1:
		if conplete_status_list[doc.doctype] == status:
			close = True
	
	todos = frappe.db.get_list("ToDo", {
		"reference_type": doc.doctype, 
		"reference_name": doc.name
	}, ["name", "status"])
	for d in todos:
		if d.status == "Cancelled":
			continue

		todo = frappe.get_doc("ToDo", d.name)
		if close:
			todo.status = "Completed"
		else:
			todo.status = "Planned"
		todo.save()
def update_request(reff_doc, state):
	# from Asset Repair' and Asset Maintenance Log
	if reff_doc.doctype not in ('Asset Repair', 'Asset Maintenance Log', 'ToDo'):
		return
	
	request_id = reff_doc.get("request_id")

	# from ToDo
	if reff_doc.doctype == "ToDo":
		if reff_doc.reference_type == "Maintenance Request":
			request_id = reff_doc.reference_name
		else:
			return
		
	if not request_id:
		return
	
	doc = frappe.get_doc("Maintenance Request", request_id)
	workflow = get_workflow(doc.doctype)
	transitions = get_transitions(doc, workflow)
	
	# find the transition
	transition = None
	for t in transitions:
		if t.action == state:
			transition = t

	if not transition:
		return
	
	if doc.workflow_state != transition.next_state:
		apply_workflow(doc, state)

def directly_workflow_from_webform(doc, method=""):
	# do all for desk and webform
	# if not frappe.flags.in_web_form:
	# 	return
	
	# Directly pass state from Draft to Issued
	if doc.get("workflow_state") != "Draft":
		return
	
	if not validate_workflow(doc, "Submit"):
		return
	
	apply_workflow(doc, "Submit")
	
from frappe.model.workflow import get_workflow, apply_workflow, has_approval_access, get_transitions
from frappe.workflow.doctype.workflow_action.workflow_action import get_next_possible_transitions
def validate_workflow(doc, action):
	"""Allow workflow action on the current doc"""
	doc = frappe.get_doc(frappe.parse_json(doc))
	workflow = get_workflow(doc.doctype)
	transitions = get_next_possible_transitions(workflow.name, doc.get("workflow_state"), doc)
	user = frappe.session.user

	# find the transition
	transition = None
	for t in transitions:
		if t.action == action:
			transition = t

	if not transition:
		return False

	if not has_approval_access(user, doc, transition):
		return False
	
	return True

@frappe.whitelist()
def planned_todo_count():
	return frappe.db.count("ToDo", {"status": "Planned"})

def add_user_permissions(doc, method=""):
	if not has_permission("User Permission", ptype="write", raise_exception=False):
		return

	employee_user_permission_exists = frappe.db.exists(
		"User Permission", {"allow": "User", "for_value": doc.name, "user": doc.name}
	)

	adds = False
	for d in doc.get("roles"):
		if d.role == "Navix Personnel":
			adds = True
			break

	if adds:
		if employee_user_permission_exists:
			return
		add_user_permission("User", doc.name, doc.name)
	else:
		if not employee_user_permission_exists:
			return
		remove_user_permission("User", doc.name, doc.name)