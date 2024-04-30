# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class VisitorRegistration(Document):
	def validate(self):

		if self.workflow_state == "Started":
			self.update_todo(start=1)
		elif self.workflow_state == "Resolved":
			self.update_todo(start=2)

	def update_todo(self, start=0):
		# start = 1 for yes, 2 for stop
		filters = {
			"reference_type": self.doctype,
			"reference_name": self.name,
			"status": "Planned",
			# "allocated_to": assign_to, # temporary all assign
		}
		data = frappe.get_all("ToDo", filters=filters)
		if data:
			for d in data:
				todo = frappe.get_doc("ToDo", d.name)
				if start == 2:
					todo.set_complete()
					todo.db_update()

@frappe.whitelist()
def create_to_do(name):
	todo = frappe.new_doc("ToDo")
	todo.update({"reference_type": "Visitor Registration", "reference_name": name})
	return todo
