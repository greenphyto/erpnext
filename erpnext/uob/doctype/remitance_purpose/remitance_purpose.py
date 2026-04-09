# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RemitancePurpose(Document):
	def before_insert(self):
		if self.country_id:
			self.country_id = self.country_id.upper()