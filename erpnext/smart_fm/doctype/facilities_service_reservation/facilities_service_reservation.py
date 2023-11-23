# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, cint
from frappe import _
from datetime import timedelta
from frappe.desk.reportview import get_filters_cond

class FacilitiesServiceReservation(Document):
	def validate(self):
		self.validate_time()
		self.validate_service()
		self.update_booking()

	def after_insert(self):
		self.processed = 0
		self.status = "Issued"

	def before_validate(self):
		if (self.all_day and not self.multi_days):
			self.to_date = self.from_date
		elif not self.all_day and not self.multi_days:
			self.to_date = self.from_date
		
		# setup datetime
		self.from_time = get_datetime("{} {}".format(self.from_date, self.start_time))
		self.to_time = get_datetime("{} {}".format(self.to_date, self.end_time))

	def validate_time(self):
		if get_datetime(self.from_time) < get_datetime():
			frappe.throw(_("Cannot reserve for past time"))

		if get_datetime(self.from_time) > get_datetime(self.to_time):
			frappe.throw(_("wrong time setting!"))

	def validate_service(self):
		quantity_available = frappe.get_value("Facility Service", self.service, "available_qty")
		if self.qty > quantity_available:
			frappe.throw(_("This service is not avilable at your qty"))

		# validate overlap
		data = frappe.db.sql("""
			select 
				sum(qty) as qty, service
			from 
				`tabFacilities Service Reservation`
			where 
				docstatus = 0
				and status != "Rejected"
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
		}, as_dict=1, debug=0)

		if data:
			data = data[0]
		
			if data.qty:
				available_qty_at_date = quantity_available - data.qty
				if available_qty_at_date < self.qty:
					frappe.throw(_("This service only available <b>{}</b> quantity at selected time".format( cint(available_qty_at_date) )))

				self.quantity_available = available_qty_at_date

	def on_submit(self):
		if self.to_time > get_datetime():
			self.process_rented()

	def on_cancel(self):
		# if cancel at rented so minus the qty
		# if cancel at returned so add the qty
		if self.status == "Started":
			self.process_rented(cancel=True)
		elif self.status == "":
			self.process_return(cancel=True)

	def on_trash(self):
		self.update_booking(trash=1)

	def process_rented(self, cancel=False):
		until_time = get_datetime() + timedelta(minutes=15)
		if get_datetime(self.from_time) <= until_time:
			doc = frappe.get_doc("Facility Service", self.service)
			doc.set_rented(self.qty, cancel=cancel)
			doc.db_update()
			self.processed = 1

	def process_return(self, cancel=False):
		self.return_date = get_datetime()
		if self.processed:
			doc = frappe.get_doc("Facility Service", self.service)
			doc.set_return(self.qty, cancel=cancel)
			doc.db_update()
	
	def update_booking(self, trash=0):
		doc = frappe.get_doc("Facility Service", self.service)
		qty = 0
		if not trash:
			state_flow = self.detect_workflow()
			if not state_flow:
				return
			
			if state_flow[0] in ['Rejected', 'Issued']:
				return

			if self.status == "Cancelled":
				qty = self.qty * -1
			elif self.status == "Accepted":
				qty = self.qty

		else:
			if self.status == "Cancelled":
				qty = self.qty * -1
			elif self.status == "Accepted":
				qty = self.qty

		doc.set_booking(add_qty=qty)
		doc.db_update()

	def detect_workflow(self):
		# return like return current_state, previous_state, (previous_state, current_state)
		old_doc = self.get_doc_before_save()
		status = ""
		if old_doc:
			status = old_doc.get("status")

		# changed true
		if status != self.status:
			return self.status, status, (status, self.status)
		else:
			return


	def control_rented(self):
		if self.status == "Started":
			if self.to_time >= get_datetime():
				self.process_rented()
		
		elif self.status == "Finished":
			self.process_return()


def set_booking_to_rented():
	until_time = get_datetime() + timedelta(minutes=15)
	data = frappe.db.get_list("Facilities Service Reservation", {
		"processed": 0,
		"from_time":['<=', until_time]
	}, "name")
	for d in data:
		doc = frappe.get_doc("", d.name)
		doc.process_rented()

@frappe.whitelist()
def get_events(start, end, user=None, for_reminder=False, filters=None):
	if not user:
		user = frappe.session.user

	if isinstance(filters, str):
		filters = json.loads(filters)

	filter_condition = get_filters_cond("Event", filters, [])

	events = frappe.db.sql("select * from `tabFacilities Service Reservation`", as_dict=1)

	# setup filter
	# format title etc


	return events