# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

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


# erpnext.smart_fm.doctype.permit_to_work.permit_to_work.update_old_doc
def update_old_doc():
	print_format = 'Permit to Work (Old Format)'
	for d in frappe.get_all("Permit to Work", {"workflow_state": "Approved", "approved_print":['in',[None, ""] ]}):
		doc = frappe.get_doc("Permit to Work", d.name)
		doc.attach_approved(force=1, print_format=print_format)
		doc.db_update()
		print("Update for ", doc.name)