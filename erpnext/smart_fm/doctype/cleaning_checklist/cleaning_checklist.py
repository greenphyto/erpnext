# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CleaningChecklist(Document):
	def validate(self):
		self.add_user_name()

	def add_user_name(self):
		full_name = frappe.db.get_value("User", frappe.session.user, "full_name")
		self.cleaned_by = full_name