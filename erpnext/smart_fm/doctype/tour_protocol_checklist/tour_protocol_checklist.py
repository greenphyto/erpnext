# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.desk.reportview import get_filters_cond
from six import string_types

class TourProtocolChecklist(Document):
	pass


COLOR_MAP = {
	"primary": "#007BFF",
	"secondary": "#6C757D",
	"success": "#28A745",
	"danger": "#DC3545",
	"warning": "#FFC107",
	"info": "#17A2B8",
	"light": "#F8F9FA",
	"dark": "#343A40",
}

TEXT_COLOR = {
	"primary": "#FFFFFF", 
	"secondary": "#FFFFFF",
	"success": "#FFFFFF",
	"danger": "#FFFFFF",
	"warning": "#212529",  
	"info": "#FFFFFF",
	"light": "#212529", 
	"dark": "#FFFFFF",
}

@frappe.whitelist()
def get_events(start, end, user=None, for_reminder=False, filters=None):
	if not user:
		user = frappe.session.user

	if isinstance(filters, str):
		filters = json.loads(filters)

	filter_condition = []

	events = frappe.db.sql("""
		SELECT 
			t.name, t.group_name, t.status, 1 AS all_day
		FROM
			`tabTour Protocol Checklist` t
		WHERE
			t.docstatus = 0
	""".format(filter_condition), as_dict=1, debug=0)

	style_map = {
		"Issued": "warning",
		"Accepted": "primary",
		"Started": "success",
		"Finished": "secondary",
		"Cancelled": "light",
		"Rejected": "danger",
	}

	for d in events:
		ref_color = style_map.get(d.status)
		if ref_color:
			d.color = COLOR_MAP[ref_color]
			d.textColor = TEXT_COLOR[ref_color]
		
	return events

from frappe.utils import getdate, add_days
def send_email_notif(use_date=""):
	cur_date = getdate(use_date)
	dt = add_days(cur_date, 1) 
	doc_list = frappe.db.sql("""
		SELECT 
			name,
			group_name,
			email,
			vip_status,
			TIME_FORMAT(time, %s) AS time,
			tour_ic
		FROM
			`tabTour Protocol Checklist`
		WHERE
			date = %s
	""",('%H:%i', dt), as_dict=1)
	if doc_list:
		# send email
		notif = frappe.get_doc("Notification", "Upcoming Tour Visit")
		notif.send({"doc_list": doc_list})
