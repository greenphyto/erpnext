# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime
from frappe import _

class FacilitiesServiceReservation(Document):
	def validate(self):
		self.validate_time()
		self.validate_service()

	def validate_time(self):
		if get_datetime(self.from_time) > get_datetime(self.to_time):
			frappe.throw(_("From time cannot higher than to time"))

	def validate_service(self):

		if self.qty > self.quantity_available:
			frappe.throw(_("This service is not avilable at your qty"))

		# validate overlap
		data = frappe.db.sql("""
			select 
				sum(qty) as qty, service
			from 
				`tabFacilities Service Reservation`
			where 
				docstatus = 1
				and 
					( 
						( 
							from_time >= %(from_time)s and from_time <= %(to_time)s
						) or (
							to_time >= %(from_time)s and to_time <= %(to_time)s
						) or (
							from_time <= %(from_time)s and to_time >= %(to_time)s
						)
					)
				and service = %(service)s
					   and name != %(name)s
		""", {
			"service":self.service,
			"from_time":self.from_time,
			"to_time":self.to_time,
			"name":self.name
		}, as_dict=1)

		if data:
			data = data[0]
		
			if data.qty:
				available_qty_at_date = self.quantity_available - data.qty
				if available_qty_at_date < self.qty:
					frappe.throw(_("This service only available {} quantity at the date".format(available_qty_at_date)))

	def on_submit(self):
		doc = frappe.get_doc("Facility Service", self.service)
		doc.set_rented(self.qty)

	def on_cancel(self):
		doc = frappe.get_doc("Facility Service", self.service)
		doc.set_rented(self.qty, cancel=True)

