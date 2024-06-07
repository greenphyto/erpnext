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

		
