import frappe
from frappe.desk.form.utils import get_pdf_link
from frappe.utils.verified_command import get_signed_params, verify_request
from frappe.utils import getdate, cint, get_url, cstr, add_days
from frappe import _


################################
### ToDo: Turn Off Reminders ###
################################
#region 

def get_reminder_off_url(doc, user):
	apply_action_method = (
		"/api/method/erpnext.smart_fm.controllers.web_access.apply_action_to_off_reminder"
	)

	params = {
		"doctype": doc.get("doctype"),
		"docname": doc.get("name"),
		"user": user,
		"last_modified": doc.get("modified"),
	}

	return get_url(apply_action_method + "?" + get_signed_params(params))

@frappe.whitelist(allow_guest=True)
def apply_action_to_off_reminder(doctype, docname, user=None, last_modified=None):
	if not verify_request():
		return

	doc = frappe.get_doc(doctype, docname)
	action_link = get_confirm_reminder_off_url(doc, user)

	if not doc.get("reminder_off"):
		return_reminder_off_confirmation_page(doc, action_link)
	else:
		return_link_expired_page_reminder_todo(doc)

def return_reminder_off_confirmation_page(doc, action_link):
	template_params = {
		"title": "Turn off reminder notification",
		"doctype": doc.get("doctype"),
		"docname": doc.get("name"),
		"action_link": action_link
	}
	template_params["pdf_link"] = get_pdf_link(doc.get("doctype"), doc.get("name"))
	frappe.respond_as_web_page(
		title=None,
		html=None,
		indicator_color="blue",
		template="confirm_reminder_off_todo",
		context=template_params,
	)


def return_link_expired_page_reminder_todo(doc):
	msg = _("Reminder still active for {0} {0}").format(
			frappe.bold(doc.get("doctype")),
			frappe.bold(doc.get("name")),
		)
	if doc.reminder_off:
		msg = _("Reminder has already non-active")
		
	frappe.respond_as_web_page(
		_("Link Expired"),
		msg,
		indicator_color="blue",
	)

def get_confirm_reminder_off_url(doc, user):
	confirm_action_method = (
		"/api/method/erpnext.smart_fm.controllers.web_access.confirm_turn_of_todo"
	)

	params = {
		"doctype": doc.get("doctype"),
		"docname": doc.get("name"),
		"user": user,
	}

	return get_url(confirm_action_method + "?" + get_signed_params(params))

@frappe.whitelist(allow_guest=True)
def confirm_turn_of_todo(doctype, docname, user):
	if not verify_request():
		return

	logged_in_user = frappe.session.user
	if logged_in_user == "Guest" and user:
		# to allow user to apply action without login
		frappe.set_user(user)

	doc = frappe.get_doc(doctype, docname)
	doc.db_set("reminder_off", 1)

	frappe.db.commit()
	return_success_page("Reminder is off")

	# reset session user
	if logged_in_user == "Guest":
		frappe.set_user(logged_in_user)

def return_success_page(msg, title="Success"):
	frappe.respond_as_web_page(
		_(title),
		_(msg),
		indicator_color="green",
	)

#endregion

#######################################
### Issue: Create ticket from email ###
#######################################
#region

def get_create_ticket_url(doctype, docname, email):
	apply_action_method = (
		"/api/method/erpnext.smart_fm.controllers.web_access.create_ticket_page"
	)

	doc = frappe.get_doc(doctype, docname)

	params = {
		"doctype": doc.get("doctype"),
		"docname": doc.get("name"),
		"user": email,
		"last_modified": doc.get("modified"),
	}

	return get_url(apply_action_method + "?" + get_signed_params(params))

@frappe.whitelist(allow_guest=True)
def create_ticket_page(doctype, docname, user=None, last_modified=None):
	if not verify_request():
		return

	doc = frappe.get_doc(doctype, docname)
	action_link = get_send_ticket_url()

	# link expired if more than 30 days from creation
	exp_date = add_days( getdate(doc.creation), 300)
	if getdate() < exp_date:
		return_create_ticket_page(doc, user, action_link)
	else:
		return_link_expired_page_create_ticket(doc)


def get_send_ticket_url():
	confirm_action_method = (
		"/api/method/erpnext.smart_fm.controllers.web_access.submit_online_ticket"
	)

	return get_url(confirm_action_method)

def return_create_ticket_page(doc, user, action_link):
	user = frappe.db.exists("User", {"email": user}) or frappe.db.exists("User", user)

	full_name = ""
	if user:
		full_name = frappe.get_value("User", user, "full_name")

	template_params = {
		"title": "Create ticket/issue",
		"doctype": doc.get("doctype"),
		"docname": doc.get("name"),
		"user": user,
		"full_name": full_name,
		"action_link": action_link
	}
	template_params["pdf_link"] = get_pdf_link(doc.get("doctype"), doc.get("name"))
	frappe.respond_as_web_page(
		title=None,
		html=None,
		indicator_color="blue",
		template="submit_ticket_issue",
		context=template_params,
	)

def return_link_expired_page_create_ticket(doc):
	msg = _("Sorry, Cannot create ticket.")
		
	frappe.respond_as_web_page(
		_("Link Expired"),
		msg,
		indicator_color="blue",
	)

@frappe.whitelist(allow_guest=True)
def submit_online_ticket(user, data):
	if not verify_request():
		return

	logged_in_user = frappe.session.user
	if logged_in_user == "Guest" and user:
		# to allow user to apply action without login
		frappe.set_user(user)

	# create issue
	doc = frappe.new_doc("Issue")
	doc.update(data)
	doc.insert()

	frappe.db.commit()
	return_success_page("Thank you! Your ticket has been sent.")

	# reset session user
	if logged_in_user == "Guest":
		frappe.set_user(logged_in_user)


#endregion