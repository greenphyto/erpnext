# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from erpnext.smart_fm.doctype.visitor_registration.visitor_registration import is_security_user, get_now

class KeyControl(Document):
	def validate(self):
		self.set_status()
		self.set_checkout_time()

	def before_save(self):
		self.validate_date()

	def validate_date(self):
		if self.issued_time == "Now":
			self.issued_time = ""
		if self.returned_time == "Now":
			self.returned_time = ""
	
	def set_status(self):
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return
		
		# by workflow 
		if old_doc.get("workflow_state") != self.get("workflow_state"):
			pass
		# by web form
		elif old_doc.get("returned") != self.get("returned") and self.get("returned") == 1:
			if not is_security_user():
				frappe.throw(_("Only <b>Security</b> can change check in/out!"))
			self.workflow_state = "Returned"
		elif old_doc.get("issued") != self.get("issued") and self.get("issued") == 1:
			if not is_security_user():
				frappe.throw(_("Only <b>Security</b> can change check in/out!"))
			self.workflow_state = "Issued"

		self.db_set("workflow_state", self.workflow_state)

	def set_checkout_time(self):
		if self.workflow_state not in ("Issued", "Returned"):
			self.issued_time = None
			self.returned_time = None
			self.returned = 0
			self.issued = 0
		else:
			if self.workflow_state == "Issued":
				self.issued_time = get_now(self.issued_time)
				self.issued = 1
				self.returned_time = None
				self.returned = 0
			elif self.workflow_state == "Returned":
				self.returned_time = get_now(self.returned_time)
				self.returned = 1

@frappe.whitelist()
def create_to_do(name):
	todo = frappe.new_doc("ToDo")
	todo.update({"reference_type": "Key Control", "reference_name": name})
	return todo
