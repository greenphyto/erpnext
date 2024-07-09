# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, cint, add_days, get_time
from frappe import _
from datetime import timedelta
from frappe.desk.reportview import get_filters_cond
from frappe.model.workflow import apply_workflow
from six import string_types
from datetime import datetime

WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAY_BY_NAME = {
	"Monday":0, 
	"Tuesday":1, 
	"Wednesday":2, 
	"Thursday":3, 
	"Friday":4, 
	"Saturday":5, 
	"Sunday":6
}

COLOR_MAP = {
	"primary": "#007BFF",
	"secondary": "#6C757D",
	"success": "#28A745",
	"danger": "#DC3545",
	"warning": "#FFC107",
	"info": "#17A2B8",
	"light": "#F8F9FA",
	"dark": "#343A40",
}

TEXT_COLOR = {
	"primary": "#FFFFFF", 
	"secondary": "#FFFFFF",
	"success": "#FFFFFF",
	"danger": "#FFFFFF",
	"warning": "#212529",  
	"info": "#FFFFFF",
	"light": "#212529", 
	"dark": "#FFFFFF",
}

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

	def before_insert(self):
		if self.status == "Draft":
			self.status = "Issued"

	def before_validate(self):
		if (self.all_day and not self.repeat_data):
			self.to_date = self.from_date
		elif not self.all_day and not self.repeat_data:
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
		# diff = getdate(self.to_date) - getdate(self.from_date)
		# current = getdate(self.from_date)
		# valid_days = self.service_doc.get_valid_days()
		# for d in range(diff.days or 1):
		# 	current = add_days(current, d)
		# 	day_name = current.strftime("%A")
		# 	if day_name not in valid_days:
		# 		frappe.throw("This service only available on <b>{}</b>.".format(", ".join(valid_days)))

		# validate time
		start = get_time(self.service_doc.time_start or "")
		ends = get_time(self.service_doc.time_end or "")
		if (get_time(self.start_time) < start or get_time(self.end_time) > ends) and not self.all_day:
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
							from_time > %(from_time)s and from_time < %(to_time)s
						) or (
							to_time > %(from_time)s and to_time < %(to_time)s
						) or (
							from_time < %(from_time)s and to_time > %(to_time)s
						) or (
					   		from_time = %(from_time)s and to_time = %(to_time)s
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
			if not self.flags.autorun and self.status == "Issued":
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

	# log create
	def make_schedule(self):
		day_count = (getdate(self.to_date) - getdate(self.from_date)).days # escape for the last day (to date)
		start_date = getdate(self.from_date)
		print(day_count)
		delete_log(self.name)
		def _run_date(cond):
			for i in range(day_count):
				date = add_days(start_date, i)
				if cond(date):
					create_log(date, self.from_time, self.to_time, self.name, self.service)

		if self.repeat_data == "daily":
			def cond(date):
				return True
			_run_date(cond=cond)
		elif self.repeat_data == "every_weekday":
			def cond(date):
				if date.weekday() in [0,1,2,3,4]:
					return True
			_run_date(cond=cond)
		elif "weekly_on_day_name" in self.repeat_data:
			day_name = self.repeat_data.split(":")[-1]
			selected_day = WEEKDAY_BY_NAME[day_name]
			def cond(date):
				if date.weekday() == selected_day:
					return True
			_run_date(cond=cond)
		elif "monthly_on_nth_day" in self.repeat_data:
			temp = self.repeat_data.split(":")
			nth_week = {
				"first":1,
				"second":2,
				"third":3,
				"fourth":4,
				"fifth":5,
			}.get(temp[1])
			selected_day = WEEKDAY_BY_NAME.get(temp[2])
			def cond(date):
				if date.weekday() == selected_day:
					if get_nth_week_of_date(date)==nth_week:
						return True
			_run_date(cond=cond)
		elif "anually_on_month_date" in self.repeat_data:
			temp = self.repeat_data.split(":")[-1]
			use_date = datetime.strptime(f"{temp} 2000", "%B %d %Y") #2000 is just for helper
			def cond(date):
				if date.month == use_date.month and date.day == use_date.day:
					return True
			_run_date(cond=cond)

# log delete
def delete_log(reff):
	frappe.db.sql("delete from `tabReservation Time Log` where reservation_no=%s", reff)

def create_log(date, from_time, to_time, reff, facility_service):
	doc = frappe.new_doc("Reservation Time Log")
	date = getdate(date)
	doc.start = get_datetime(from_time).replace(day=date.day, month=date.month, year=date.year)
	doc.end = get_datetime(to_time).replace(day=date.day, month=date.month, year=date.year)
	doc.date = date
	doc.reservation_no = reff
	doc.facility_service = facility_service
	doc.insert(ignore_permissions=1)
	return doc.name


# delete log more than 2 years old
# generate log for next 2 years, if end forever but the log left only to this year

def get_nth_week_of_date(date):
	first_date = date.replace(day=1)
	first_weekday = first_date.weekday()
	use_weekday = first_weekday + 1
	if use_weekday == 7:
		use_weekday = 0

	diff = use_weekday + date.day
	res = diff // 7 + 1
	return res

def set_auto_accept(doc, method=""):
	if doc.status == "Issued" and cint(frappe.get_value("Facility Service", doc.service, "auto_accept")):
		doc.flags.autorun = 1
		apply_workflow(doc, "Accept")

def set_booking_to_rented():
	until_time = get_datetime() + timedelta(minutes=15) # 15 minute tolerance
	data = frappe.db.get_list("Facilities Service Reservation", {
		"processed": 0,
		"from_time":['<=', until_time],
		"status":"Accepted"
	}, "name")
	for d in data:
		doc = frappe.get_doc("Facilities Service Reservation", d.name)
		doc.flags.autorun = 1
		apply_workflow(doc, "Start")

def set_finish_rent():
	until_time = get_datetime() + timedelta(minutes=15) # 15 minute tolerance
	data = frappe.db.get_list("Facilities Service Reservation", {
		"to_time":['<=', until_time],
		"status":"Started"
	}, "name", debug=1)
	for d in data:
		doc = frappe.get_doc("Facilities Service Reservation", d.name)
		doc.flags.autorun = 1
		apply_workflow(doc, "Finish")

@frappe.whitelist()
def get_events(start, end, user=None, for_reminder=False, filters=None):
	if not user:
		user = frappe.session.user

	if isinstance(filters, str):
		filters = json.loads(filters)

	if not any(x[0] == 'status' for x in filters):
		filters.append(['status', 'not in', ['Cancelled', 'Rejected']])

	filter_condition = get_filters_cond("Facilities Service Reservation", filters, [])

	events = frappe.db.sql("""
		select * 
		from `tabFacilities Service Reservation` 
		where docstatus != 2 {}
	""".format(filter_condition), as_dict=1)

	style_map = {
		"Issued": "warning",
		"Accepted": "primary",
		"Started": "success",
		"Finished": "secondary",
		"Cancelled": "light",
		"Rejected": "danger",
	}

	for d in events:
		ref_color = style_map.get(d.status)
		if ref_color:
			d.color = COLOR_MAP[ref_color]
			d.textColor = TEXT_COLOR[ref_color]
		
	return events

@frappe.whitelist()
def get_facilities_list(filters={}):
	if isinstance(filters, string_types):
		filters = json.loads(filters)


	data = frappe.db.get_list("Facility Service", filters, ['status', 'name', 'available_qty as available', 'rented_qty as rented'])
	color_map = {
		"Partially Rented":'#fd8f00',
		"All Rented":"#a22ce9",
		"Available":"#00bf00",
	}

	for d in data:
		d.status_color = color_map.get(d.status)

	return data