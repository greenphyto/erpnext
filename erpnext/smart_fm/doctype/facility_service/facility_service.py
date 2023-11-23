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
	
	def set_booking(self, add_qty=0):
		# if booking qty only max qty for order
		# self.booking_qty = cint(frappe.db.get_value("Facilities Service Reservation", {
		# 	"service":self.name,
		# 	"docstatus":0,
		# 	"to_time":['>=', get_datetime()],
		# 	"processed": 0,
		# 	"status":['not in', ['Rejected', 'Issued']]
		# }, "max(qty) as qty", debug=1)) + add_qty
		self.booking_qty = self.booking_qty + add_qty

	def set_rented(self, qty, cancel=False):
		if not cancel:
			self.rented_qty += qty
		else:
			self.rented_qty -= qty

		self.update_status()

	def set_return(self, qty, cancel=False):
		if not cancel:
			self.rented_qty -= qty
		else:
			self.rented_qty += qty

		self.update_status()
	
	def validate_qty(self):
		# self.set_booking()
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


