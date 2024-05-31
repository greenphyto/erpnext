# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class PermittoWork(Document):
	def before_save(self):
		self.validate_signature()

	def validate_signature(self):
		if self.conductor_signature and not self.contractor_safety_assessor:
			frappe.throw(_("Please set name to <b>Contractor Safety Assessor</b>"))
		if self.ptw_signature and not self.permit_to_work_applicant:
			frappe.throw(_("Please set name to <b>Permit to Work Applicant</b>"))
		if self.authorized_signature and not self.name1:
			frappe.throw(_("Please set name to <b>Section D</b>"))
		
