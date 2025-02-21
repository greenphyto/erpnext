# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, add_days
from frappe.desk.reportview import get_filters_cond
from six import string_types

class TourProtocolChecklist(Document):
	def before_validate(self):
		# setup datetime
		self.from_time = get_datetime("{} {}".format(self.date, self.start_time))
		self.to_time = get_datetime("{} {}".format(self.date, self.end_time))


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

	filter_condition = get_filters_cond("Tour Protocol Checklist", filters, [])

	events = frappe.db.sql("""
		SELECT 
			`tabTour Protocol Checklist`.group_name AS full_name,
			`tabTour Protocol Checklist`.date,
			`tabTour Protocol Checklist`.start_time AS st,
			`tabTour Protocol Checklist`.end_time AS nd,
			`tabTour Protocol Checklist`.name,
			`tabTour Protocol Checklist`.group_name,
			`tabTour Protocol Checklist`.vip_status,
			`tabTour Protocol Checklist`.participants,
			`tabTour Protocol Checklist`.tour_ic,
			u.full_name
		FROM
			`tabTour Protocol Checklist`
				LEFT JOIN
			`tabUser` u ON u.name = `tabTour Protocol Checklist`.tour_ic
		WHERE
			`tabTour Protocol Checklist`.docstatus = 1 {}
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
		d.start_time = get_datetime("{} {}".format(d.date, d.st or "09:00"))
		d.end_time = get_datetime("{} {}".format(d.date, d.nd or "18:00"))
		d.all_day = 0
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
			date = %s and docstatus = 1
	""",('%H:%i', dt), as_dict=1)
	notif = frappe.get_doc("Notification", "Upcoming Tour Visit")
	for d in doc_list:
		doc = frappe.get_doc("Tour Protocol Checklist", d.name)
		recipients, cc, bcc = notif.get_list_of_recipients(doc, {})
		vgs = []
		for d in doc.get("vegetable"):
			vgs.append(f"{d.vegetable} {d.qty} packs")
		doc.vegetable_packages = ", ".join(vgs)
		for rec in recipients:
			notif.single_recipient = rec
			doc.recipient_name = frappe.get_value("User", rec, "full_name")
			notif.send(doc)

@frappe.whitelist()
def get_group(txt=""):
	filters = {}
	if txt:
		filters['group_name'] = ['like', "%"+txt+"%"]

	return frappe.db.get_all("Tour Protocol Checklist", filters, ['group_name as label', 'name as value'])