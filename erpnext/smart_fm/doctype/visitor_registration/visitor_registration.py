# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.model.workflow import apply_workflow, get_workflow
from frappe.utils import get_datetime, cstr
from frappe import _

class VisitorRegistration(Document):
	def before_save(self):
		if self.person == "No":
			self.person_list = []
		self.validate_workflow_state()

	def validate(self):

		# if self.workflow_state == "Started":
		# 	self.update_todo(start=1)
		# elif self.workflow_state == "Resolved":
		# 	self.update_todo(start=2)

		self.set_status()
		self.set_checkout_time()

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

	def validate_workflow_state(self):
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return

		if old_doc.get("status") == self.get("status"):
			return
		
		if old_doc.get("status") not in ("Accepted", "Sign Out", "Sign In") and (self.get("status") == "Sign In" or self.get("status") == "Sign Out"):
			frappe.throw(_("User is not yet approved for short/long term pass"))

		if old_doc.get("status") == "Accepted" and self.status == "Sign Out":
			frappe.throw(_("Cannot Sign out before Sign in"))
	
	def set_status(self):
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return
		
		# by workflow 
		if old_doc.get("status") != self.get("status"):
			self.add_time_logs()
		# by web form
		elif old_doc.get("check_out") != self.get("check_out") and self.get("check_out") == 1:
			if not is_security_user():
				frappe.throw(_("Only <b>Security</b> can change check in/out!"))
			self.status = "Sign Out"
			self.add_time_logs()
		elif old_doc.get("check_in") != self.get("check_in") and self.get("check_in") == 1:
			if not is_security_user():
				frappe.throw(_("Only <b>Security</b> can change check in/out!"))
			self.status = "Sign In"
			self.add_time_logs()


	def set_checkout_time(self):
		if self.status not in ("Sign In", "Sign Out"):
			self.check_in_time = None
			self.check_in = 0
			self.check_out_time = None
			self.check_out = 0
		else:
			if self.status == "Sign In":
				self.check_in_time = get_now()
				self.check_in = 1
				self.check_out_time = None
				self.check_out = 0
			elif self.status == "Sign Out":
				self.check_out_time = get_now()
				self.check_out = 1
				if self.duration != "One-time access":
					self.check_in_time = None
					self.check_in = 0

		
	def add_time_logs(self):
		if not self.meta.get_field("time_log"):
			return
		
		if self.duration == "One-time access":
			return
	
		if self.status not in ("Sign In", "Sign Out"):
			return
	
		row = self.append("time_log")
		row.log = "In" if self.status == "Sign In" else "Out"
		row.datetime = get_now()


def is_security_user(user=""):
	roles = frappe.get_roles(user)
	return "Security" in roles

def is_bm_manager(user=""):
	roles = frappe.get_roles(user)
	return "Building Management (Manager)" in roles

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
	
	# if is_bm_manager() and self.duration != "One-time access":
	# 	apply_workflow(self, "Accept")


@frappe.whitelist()
def create_to_do(name):
	todo = frappe.new_doc("ToDo")
	todo.update({"reference_type": "Visitor Registration", "reference_name": name})
	return todo

@frappe.whitelist()
def find_data_by_phone_number(number):
	number = cstr(number)
	fields = [
		"name1",
		"unit_number__office_number",
		"company",
		"email_address",
		"area_resource",
		"reason",
		"duration",
		"person"
	]
	data = frappe.db.get_value("Visitor Registration", {"phone_number":number}, fields, as_dict=1)

	return data

@frappe.whitelist()
def update_checkin(name, types):
	name = frappe.db.exists("Visitor Registration", name)
	if name:
		doc = frappe.get_doc("Visitor Registration", name)
		enable = 0
		if doc.duration != "One-time access":
			enable = 1
		if types == "IN":
			apply_workflow(doc, "Check In")
			return {"status":doc.status, "time":doc.check_in_time, "enable_out":enable}
		else:
			apply_workflow(doc, "Check Out")
			return {"status":doc.status, "time":doc.check_out_time, "enable_in":enable}
		


