# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, cint, add_days, get_time
from frappe import _
from datetime import timedelta
from frappe.desk.reportview import get_filters_cond
from frappe.model.workflow import apply_workflow

WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

class FacilitiesServiceReservation(Document):
	def validate(self):
		self.validate_time()
		self.validate_time_service()
		self.validate_service()
		self.update_booking()

	def on_update_after_submit(self):
		self.update_booking()
		self.process_rented()

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
		tolerant_time = get_datetime() - timedelta(minutes=30)
		if get_datetime(self.from_time) < tolerant_time:
			frappe.throw(_("Cannot reserve for past time"))

		if get_datetime(self.from_time) > get_datetime(self.to_time):
			frappe.throw(_("wrong time setting!"))
	
	def get_service_detail(self):
		if not self.get("service_doc"):
			self.service_doc = frappe.get_doc("Facility Service", self.service)

	def validate_time_service(self):
		self.get_service_detail()
		# validate date
		diff = getdate(self.to_date) - getdate(self.from_date)
		current = getdate(self.from_date)
		valid_days = self.service_doc.get_valid_days()
		for d in range(diff.days or 1):
			current = add_days(current, d)
			day_name = current.strftime("%A")
			if day_name not in valid_days:
				frappe.throw("This service only available on <b>{}</b>.".format(", ".join(valid_days)))

		# validate time
		start = get_time(self.service_doc.time_start)
		ends = get_time(self.service_doc.time_end)
		if get_time(self.start_time) < start or get_time(self.end_time) > ends:
			frappe.throw("This service only available at <b>{}-{}</b>.".format(start, ends))

	def get_qty_at_time(self):
		data = frappe.db.sql("""
			select 
				sum(qty) as qty, service
			from 
				`tabFacilities Service Reservation`
			where 
				docstatus != 2
				and status not in ("Rejected", "Cancelled")
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
			return cint(data[0].get("qty"))
		else:
			return 0

	def validate_service(self):
		quantity_available = frappe.get_value("Facility Service", self.service, "available_qty")
		if self.qty > quantity_available:
			frappe.throw(_("This service is not avilable at your qty"))

		# validate overlap
		qty = self.get_qty_at_time()		
		if qty:
			available_qty_at_date = quantity_available - qty
			if available_qty_at_date < self.qty:
				frappe.throw(_("This service only available <b>{}</b> quantity at selected time".format( cint(available_qty_at_date) )))

			self.quantity_available = available_qty_at_date

	def on_submit(self):
		pass

	def on_cancel(self):
		# if cancel at rented so minus the qty
		# if cancel at returned so add the qty
		if self.is_backdate():
			return
		
		state = self.detect_workflow()
		doc = frappe.get_doc("Facility Service", self.service)
		if not state:
			if self.status == 'Started':
				doc.set_rented(qty=self.qty * -1)
				self.processed = 0
				self.db_update()
			if self.status == 'Accepted':
				doc.set_booking(add_qty=self.qty * -1)
				self.db_update()
			if self.status == 'Finished':
				doc.set_rented(qty=self.qty)
				self.db_update()
		else:
			if state[2] == ('Started', "Cancelled"):
				doc.set_rented(qty=self.qty * -1)
				self.processed = 0
				self.db_update()
			if state[2] == ('Accepted', "Cancelled"):
				doc.set_booking(add_qty=self.qty * -1)
				self.db_update()

		doc.db_update()

	def is_backdate(self):
		if get_datetime(self.to_time) > get_datetime():
			return False
		else:
			return True

	def process_rented(self):
		if self.is_backdate():
			return

		state = self.detect_workflow()
		if not state:
			return

		doc = frappe.get_doc("Facility Service", self.service)
		if state[0] == "Started":
			# validate 
			if not self.flags.autorun:
				self.validate_force_start()

			doc.set_rented(qty=self.qty)
			doc.set_booking(add_qty=self.qty * -1)
			self.processed = 1
			self.db_update()
			
		elif state[2] == ('Accepted', 'Finished'):
			doc.set_booking(add_qty=self.qty * -1)
		elif state[2] == ('Started', 'Finished'):
			doc.set_rented(qty=self.qty * -1)
		elif state[0] == "Cancelled":
			doc.set_booking(add_qty=self.qty * -1)

		# until_time = get_datetime() + timedelta(minutes=15)
		# if get_datetime(self.from_time) <= until_time:
		# 	doc.set_rented(self.qty)
		# 	doc.db_update()
		# 	self.processed = 1

		doc.db_update()


	def validate_force_start(self):
		self.from_time = getdate()
		quantity_available = frappe.get_value("Facility Service", self.service, "available_qty")
		qty = self.get_qty_at_time()
		available_qty_at_date = quantity_available - qty
		if available_qty_at_date < self.qty:
			frappe.throw(_("Cannot rent at selected time"))

	def process_return(self, cancel=False):
		self.return_date = get_datetime()
		if self.processed:
			doc = frappe.get_doc("Facility Service", self.service)
			doc.set_return(self.qty, cancel=cancel)
			doc.db_update()
	
	def update_booking(self):
		if self.is_backdate():
			return

		doc = frappe.get_doc("Facility Service", self.service)
		qty = 0
		state_flow = self.detect_workflow()
		if not state_flow:
			return
		
		if state_flow[0] in ['Rejected', 'Issued']:
			return

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
			return self.status, status,(status, self.status)
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
		doc = frappe.get_doc("Facilities Service Reservation", d.name)
		doc.flags.autorun = 1
		apply_workflow("Start", doc)

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