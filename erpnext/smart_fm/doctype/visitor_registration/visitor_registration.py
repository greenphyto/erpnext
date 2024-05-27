# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.model.workflow import apply_workflow, get_workflow
from frappe.utils import get_datetime

class VisitorRegistration(Document):
	def validate(self):

		# if self.workflow_state == "Started":
		# 	self.update_todo(start=1)
		# elif self.workflow_state == "Resolved":
		# 	self.update_todo(start=2)

		self.set_checkout_time()
		self.set_status()
		self.add_time_logs()

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

	def set_checkout_time(self):
		if self.duration == "One-time access":
			if self.status == "Sign In" and not self.check_in:
				self.check_in_time = get_now()
				self.check_in = 1
			elif self.status == "Sign Out" and not self.check_out:
				self.check_out_time = get_now()
				self.check_out = 1
		else:
			if self.status == "Sign In":
				self.check_in_time = get_now()
				self.check_in = 1
				self.check_out_time = None
				self.check_out = 0
			elif self.status == "Sign Out":
				self.check_out_time = get_now()
				self.check_out = 1

	
	def set_status(self):
		if self.docstatus == 0 and self.status in ("Sign In", "Accepted", "Draft"):
			if self.duration == "One-time access":
				if self.check_in and not self.check_out:
					status = "Sign In"
					self.check_out_time = ""
					self.db_set("status", status)
				elif self.check_in and self.check_out:
					status = "Sign Out"
					self.db_set("status", status)
				else:
					self.check_in_time = ""
					self.check_out_time = ""
		
	def add_time_logs(self):
		if self.duration == "One-time access":
			return
	
		if self.status not in ("Sign In", "Sign Out"):
			return
	
		row = self.append("time_log")
		row.log = "In" if self.status == "Sign In" else "Out"
		row.datetime = get_now()


def get_now():
	return get_datetime().strftime("%Y-%m-%d %H:%M:%S")


def process_workflow(self, method=""):
	workflow = frappe.db.get_value(
		"Workflow", {"document_type": self.doctype, "is_active": 1}, "name"
	)
	if not workflow:
		return
	
	if self.status == "Draft":
		apply_workflow(self, "Review")

@frappe.whitelist()
def create_to_do(name):
	todo = frappe.new_doc("ToDo")
	todo.update({"reference_type": "Visitor Registration", "reference_name": name})
	return todo
