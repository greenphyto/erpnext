# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class BankNumber(Document):
	def validate(self):
		self.validate_bank_number()

	def validate_bank_number(self):
		exists = frappe.db.get_value("Bank Number", {"name":["!=", self.name], "bank_number":self.bank_number})
		if exists:
			frappe.throw(_(f"Bank number {self.bank_number} already used"))

# fetch singapore bank with SWIFT code