# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
import frappe

class MaintenanceDowntimeRequestForm(Document):
	def validate(self):
		if self.workflow_state == "Resolved":
			self.update_resolve()

	def update_resolve(self):
		# Fill resolved_by if empty
		if not self.resolved_by:
				self.resolved_by = frappe.get_value("User", frappe.session.user, "full_name")

		# Fill resolution_datetime if empty
		if not self.resolution_datetime:
				self.resolution_datetime = now_datetime().strftime("%Y-%m-%d %H:%M:%S")

		# Fill downtime_end if empty
		if not self.downtime_end:
				self.downtime_end = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
