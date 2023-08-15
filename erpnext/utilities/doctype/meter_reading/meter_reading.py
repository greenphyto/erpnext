# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class MeterReading(Document):
	def validate(self):
		self.set_status()

	def on_submit(self):
		self.set_status(True)

	def on_cancel(self):
		self.set_status(True)

	def set_status(self, update_db=False):
		if self.docstatus == 0:
			self.status = "Draft"
		elif self.docstatus == 1:
			self.status = "Submitted"
		else:
			self.status = "Cancelled"

		if self.get("workflow_state") and self.status == "Cancelled":
			self.workflow_state = 'Cancelled'
			
		if update_db:
			self.db_update()
