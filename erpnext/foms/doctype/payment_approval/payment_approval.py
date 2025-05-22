# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

""" TODO
1. calculate total OK
2. set requested by 
3. set approved by
4. get bank number, filter bank
5. filter invoice (submitted and unpaid)

"""

class PaymentApproval(Document):
	def validate(self):
		self.set_requested_by()
		self.validate_data()

	def validate_data(self):
		self.validate_invoice()
		self.calculate_amount()

	def set_requested_by(self):
		if not self.requested_by:
			self.requested_by = frappe.session.user

	def validate_invoice(self):
		# validate invoice
		# validate outstanding
		already_add = []
		for d in list(self.get("invoices")):
			if d.invoice_no in already_add:
				frappe.msgprint(f"Removed row {d.idx}, invoice is duplicate.")
				self.remove(d)
				continue

			data = frappe.db.get_value("Purchase Invoice", d.invoice_no, [
				'supplier', 
				'outstanding_amount', 
				'docstatus', 
				'currency', 
				'conversion_rate',
			], as_dict=1)
			if flt(data.docstatus) != 1:
				frappe.msgprint(f"Removed Row {d.idx}, only for submitted invoice!")
				self.remove(d)
				continue

			if flt(data.outstanding_amount) <= 0:
				frappe.msgprint(f"Removed Row {d.idx}, invoice {d.invoice_no} not have outstanding amount")
				self.remove(d)
				continue
			
			already_add.append(d.invoice_no)
			d.supplier = data.supplier
			d.amount = data.outstanding_amount
			d.currency = data.currency
			d.exchange_rate = data.conversion_rate
			# validate bank own from the supplier


	def calculate_amount(self):
		total = 0
		for d in self.get("invoices"):
			total += flt(d.basic_amount)
		
		self.total_amount = total

