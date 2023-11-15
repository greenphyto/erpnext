# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, cint
from frappe import _
from datetime import timedelta

class FacilitiesServiceReservation(Document):
	def validate(self):
		self.validate_time()
		self.validate_service()

	def validate_time(self):
		if get_datetime(self.from_time) > get_datetime(self.to_time):
			frappe.throw(_("From time cannot higher than to time"))

	def validate_service(self):
		self.quantity_available = frappe.get_value("Facility Service", self.service, "available_qty")
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

		print(data)
		if data:
			data = data[0]
		
			if data.qty:
				available_qty_at_date = self.quantity_available - data.qty
				if available_qty_at_date < self.qty:
					frappe.throw(_("This service only available <b>{}</b> quantity at the time".format( cint(available_qty_at_date) )))

	def on_submit(self):
		self.process_rented()

	def on_cancel(self):
		# if cancel at rented so minus the qty
		# if cancel at returned so add the qty
		self.process_rented(cancel=True)

	def process_rented(self, cancel=False):
		until_time = get_datetime() + timedelta(minutes=15)
		if get_datetime(self.from_time) <= until_time:
			doc = frappe.get_doc("Facility Service", self.service)
			doc.set_rented(self.qty, cancel=cancel)
			doc.db_update()
			self.processed = 1
		

def set_booking_to_rented():
	until_time = get_datetime() + timedelta(minutes=15)
	data = frappe.db.get_list("Facilities Service Reservation", {
		"processed": 0,
		"from_time":['<=', until_time]
	}, "name")
	for d in data:
		doc = frappe.get_doc("", d.name)
		doc.process_rented()
