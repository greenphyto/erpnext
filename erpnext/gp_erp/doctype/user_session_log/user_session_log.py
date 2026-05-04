# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime

class UserSessionLog(Document):
	pass

def create_user_session_log():
	"""
		{
		'data': {
			'user': 'Administrator',
			'session_ip': '127.0.0.1',
			'last_updated': '2026-04-29 12:32:39.953264',
			'session_expiry': '12:01:00',
			'full_name': None,
			'user_type': 'System User',
			'device': 'desktop',
			'session_country': None,
			'csrf_token': 'zz',
			'lang': 'en'
		},
			'user': 'Administrator',
			'sid': 'dd'
		}
	"""
	if not frappe.local.conf.enable_user_session_log:
		return

	session = frappe.session
	user = session.user
	sid = session.sid
	existing_log = frappe.db.exists("User Session Log", {"sid": sid, "is_active": 1})
	last_update = get_datetime(session.data.get("last_updated"))
	ctr = session.data.get("session_country") or {}
	if existing_log:
		frappe.db.set_value("User Session Log", existing_log, "last_update", last_update)
		frappe.db.set_value("User Session Log", existing_log, "is_active", 1)
	else:
		company = frappe.db.get_value("User", user, "company_selected") or "ALL"
		user_session_log = frappe.get_doc({
			"doctype": "User Session Log",
			"user": user,
			"ip_address": session.data.get("session_ip"),
			"device": session.data.get("device"),
			"country": ctr.get("iso_code"),
			"login_time": get_datetime(),
			"last_update": last_update,
			"sid": sid,
			"company": company,
			"is_active": 1
		})
		user_session_log.insert(ignore_permissions=True)

def get_default_value(field, sid=None):
	if not frappe.local.conf.enable_user_session_log:
		return

	if not sid:
		sid = frappe.session.sid

	value = frappe.db.get_value("User Session Log", {"sid": sid}, field)
	if not value:
		short_sid = sid[:8]
		value = frappe.db.get_value("User Session Log", {"sid": ['like', short_sid + '%']}, field)
	return value

def set_default_value(field, value, sid=None):
	if not frappe.local.conf.enable_user_session_log:
		return
	
	if not sid:
		sid = frappe.session.sid

	existing_log = frappe.db.exists("User Session Log", {"sid": sid, "is_active": 1})
	if existing_log:
		frappe.db.set_value("User Session Log", existing_log, field, value)
	else:
		short_sid = sid[:8]
		existing_log = frappe.db.exists("User Session Log", {"sid": ['like', short_sid + '%'], "is_active": 1})
		if existing_log:
			frappe.db.set_value("User Session Log", existing_log, field, value)