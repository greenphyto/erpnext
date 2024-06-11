# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from erpnext.smart_fm.doctype.visitor_registration.visitor_registration import is_security_user, get_now

MAX_DURATION = 7

class PermittoWork(Document):
	def before_save(self):
		self.validate_max_duration()
		self.validate_signature()

	def validate(self):
		self.add_approved_print()

	def on_update_after_submit(self):
		self.set_status()
		self.set_checkout_time()

	def validate_signature(self):
		if self.conductor_signature and not self.contractor_safety_assessor:
			frappe.throw(_("Please set name to <b>Contractor Safety Assessor</b>"))
		if self.ptw_signature and not self.permit_to_work_applicant:
			frappe.throw(_("Please set name to <b>Permit to Work Applicant</b>"))
		if self.authorized_signature and not self.name1:
			frappe.throw(_("Please set name to <b>Section D</b>"))

	def validate_max_duration(self):
		days = (getdate(self.date_time_work_complete) - getdate(self.date_time_work_start)).days
		if days > 7:
			frappe.throw(_("Cannot more than 7 days"))

	def add_approved_print(self):
		old_doc = self.get_doc_before_save() or {}
		if old_doc.get("workflow_state") != self.workflow_state and self.workflow_state == 'Approved':
			self.attach_approved()

	def get_print_format(self):
		default_print_format = frappe.db.get_value(
			"Property Setter",
			dict(property="default_print_format", doc_type=self.doctype),
			"value",
		)
		if default_print_format:
			print_format = default_print_format
		else:
			print_format = "Standard"

		return print_format

	def attach_approved(self, force = False, print_format=None):
		if self.approved_print and not force:
			return 
		
		print_format = print_format or self.get_print_format()

		files = frappe.attach_print(self.doctype, self.name, print_format=print_format, file_name=self.name, doc=self)

		_file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": files['fname'],
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"attached_to_field": "approved_print",
				"is_private": True,
				"content": files['fcontent'],
			}
		)

		_file.save()
		file_url = _file.file_url
		self.approved_print = file_url
	
	def set_status(self):
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return
		
		# by workflow 
		if old_doc.get("workflow_state") != self.get("workflow_state"):
			pass
		# by web form
		elif old_doc.get("check_out") != self.get("check_out") and self.get("check_out") == 1:
			if not is_security_user():
				frappe.throw(_("Only <b>Security</b> can change check in/out!"))
			self.workflow_state = "Sign Out"
		elif old_doc.get("check_in") != self.get("check_in") and self.get("check_in") == 1:
			if not is_security_user():
				frappe.throw(_("Only <b>Security</b> can change check in/out!"))
			self.workflow_state = "Sign In"


	def set_checkout_time(self):
		if self.workflow_state not in ("Sign In", "Sign Out"):
			self.check_in_time = None
			self.check_out_time = None
			self.check_out = 0
			self.check_in = 0
		else:
			if self.workflow_state == "Sign In":
				self.check_in_time = get_now(self.check_in_time)
				self.check_in = 1
				self.check_out_time = None
				self.check_out = 0
			elif self.workflow_state == "Sign Out":
				self.check_out_time = get_now(self.check_out_time)
				self.check_out = 1

# erpnext.smart_fm.doctype.permit_to_work.permit_to_work.update_old_doc
def update_old_doc():
	print_format = 'Permit to Work (Old Format)'
	for d in frappe.get_all("Permit to Work", {"workflow_state": "Approved", "approved_print":['in',[None, ""] ]}):
		doc = frappe.get_doc("Permit to Work", d.name)
		doc.attach_approved(force=1, print_format=print_format)
		doc.db_update()
		print("Update for ", doc.name)