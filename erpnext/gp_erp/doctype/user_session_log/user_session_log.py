import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class UserSessionLog(Document):
	pass


def create_user_session_log():
	if not frappe.local.conf.get("enable_user_session_log"):
		return

	session = frappe.session
	sid = session.sid
	existing_log = frappe.db.exists("User Session Log", {"sid": sid, "is_active": 1})
	last_update = get_datetime(session.data.get("last_updated"))
	country = session.data.get("session_country") or {}

	if existing_log:
		frappe.db.set_value("User Session Log", existing_log, "last_update", last_update)
		return

	frappe.get_doc({
		"doctype": "User Session Log",
		"user": session.user,
		"ip_address": session.data.get("session_ip"),
		"device": session.data.get("device"),
		"country": country.get("iso_code"),
		"login_time": get_datetime(),
		"last_update": last_update,
		"sid": sid,
		"company": frappe.db.get_value("User", session.user, "company_selected") or "ALL",
		"is_active": 1,
	}).insert(ignore_permissions=True)


def get_default_value(field, sid=None):
	if not frappe.local.conf.get("enable_user_session_log"):
		return

	sid = sid or frappe.session.sid
	value = frappe.db.get_value("User Session Log", {"sid": sid}, field)
	if not value:
		value = frappe.db.get_value("User Session Log", {"sid": ["like", sid[:8] + "%"]}, field)
	return value


def set_default_value(field, value, sid=None):
	if not frappe.local.conf.get("enable_user_session_log"):
		return

	sid = sid or frappe.session.sid
	filters = {"sid": sid, "is_active": 1}
	log_name = frappe.db.exists("User Session Log", filters)
	if not log_name:
		filters["sid"] = ["like", sid[:8] + "%"]
		log_name = frappe.db.exists("User Session Log", filters)
	if log_name:
		frappe.db.set_value("User Session Log", log_name, field, value)
