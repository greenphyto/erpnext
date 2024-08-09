# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BMSAlarm(Document):
	def after_insert(self):
		self.create_todo()

	def create_todo(self):
		priority_map = {
			"Critical":"High",
			"Major":"Medium",
			"Minor":"Low",
		}
		priority = priority_map.get(self.priority)

		# create todo
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": self.description,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"assigned_by": frappe.session.user,
				"date":self.datetime,
				"navix_ticket":1,
				"priority":priority
			}
		).insert(ignore_permissions=True)
