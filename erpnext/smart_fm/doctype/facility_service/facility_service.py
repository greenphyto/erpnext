# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, get_datetime
from frappe import _

class FacilityService(Document):
	def validate(self):
		self.validate_qty()
		self.update_status()
	
	def set_booking(self):
		self.booking_qty = frappe.db.get_value("Facilities Service Reservation", {
			"service":self.name,
			"docstatus":1,
			"to_time":['>=', get_datetime()]
		}, "max(qty) as qty")

	def set_rented(self, qty, cancel=False):
		self.update_status()

	def set_return(self, qty, canncel=False):
		self.update_status()
	
	def validate_qty(self):
		self.set_booking()
		self.total_count = cint(self.total_count) or 1

		ongoing_qty = cint(self.rented_qty)
		self.ongoing_qty = ongoing_qty

		if self.total_count < ongoing_qty:
			frappe.throw(_("Cannot update qty lower than current on going qty"))
		
		self.available_qty = cint(self.total_count) - ongoing_qty

	def update_status(self):
		if not self.enable:
			self.status = "Disabled"
			return

		self.validate_qty()
		if self.available_qty == 0:
			self.status = "All Rented"

		elif self.available_qty < self.total_count:
			self.status = "Partially Rented"

		else:
			self.status = "Available"


