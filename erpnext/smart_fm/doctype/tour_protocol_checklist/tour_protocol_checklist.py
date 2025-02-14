# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.desk.reportview import get_filters_cond
from six import string_types

class TourProtocolChecklist(Document):
	pass

@frappe.whitelist()
def get_events(start, end, user=None, for_reminder=False, filters=None):
	if not user:
		user = frappe.session.user

	if isinstance(filters, str):
		filters = json.loads(filters)

	filter_condition = get_filters_cond("Tour Protocol Checklist", filters, [])

	events = frappe.db.sql("""
		SELECT 
			`tabTour Protocol Checklist`.name,
			`tabTour Protocol Checklist`.group_name,
			`tabTour Protocol Checklist`.date,
			`tabTour Protocol Checklist`.time,
		FROM
			`tabTour Protocol Checklist` {}
	""".format(filter_condition), as_dict=1, debug=0)
		
	return events

@frappe.whitelist()
def get_tour_list(filters={}):
	if isinstance(filters, string_types):
		filters = json.loads(filters)


	data = frappe.db.get_list("Tour Protocol Checklist", filters, ['name', 'group_name', 'date', 'time'])

	return data

@frappe.whitelist()
def get_group(txt=""):
	filters = {"enable":1}
	if txt:
		filters['group_name'] = ['like', "%"+txt+"%"]

	return frappe.db.get_all("Tour Protocal Checklist", filters, ['group_name'])