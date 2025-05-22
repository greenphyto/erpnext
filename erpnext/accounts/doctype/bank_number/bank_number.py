# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class BankNumber(Document):
	def validate(self):
		self.validate_bank_number()
		# self.set_default_to_party()

	def validate_bank_number(self):
		exists = frappe.db.get_value("Bank Number", {"name":["!=", self.name], "bank_number":self.bank_number})
		if exists:
			frappe.throw(_(f"Bank number {self.bank_number} already used"))

	def set_default_to_party(self):
		default = frappe.get_value(self.party_type, self.party, "default_bank_account_no")
		if default:
			return
		
		frappe.db.set_value(self.party_type, self.party, "default_bank_account_no", self.name )

# fetch singapore bank with SWIFT code

def load_bank_list(doc):
	bank_list = frappe.db.get_all("Bank Number", {
		"party": doc.name, 
		"party_type":doc.doctype}, 
		[
			"name",
			"bank_number", 
			"bank_account_name",
			"bank",
			"branch",
			"swift"
		], order_by="creation asc") 
	doc.set_onload("bank_account_list", bank_list)