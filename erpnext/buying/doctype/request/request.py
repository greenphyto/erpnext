# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt
from frappe import _

class Request(Document):
	def validate(self):
		self.calculate_price()
		self.calculate_weight()
		self.validate_date()

	def validate_date(self):
		if getdate(self.delivery_date) < getdate(self.posting_date):
			frappe.throw(_("Delivery Date cannot before posting date."))

	def calculate_price(self):
		self.total_price = 0
		for d in self.get("items"):
			d.amount = flt(d.rate) * flt(d.qty)
			self.total_price += d.amount

	def calculate_weight(self):
		self.total_weight = 0
		for d in self.get("items"):
			d.weight = flt(d.unit_weight) * flt(d.qty)
			self.total_weight += d.weight

