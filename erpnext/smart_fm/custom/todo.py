import frappe
from frappe.desk.doctype.todo.todo import ToDo
from erpnext.smart_fm.controllers.web_access import get_reminder_off_url
from erpnext.smart_fm.controllers.smart_fm import update_request
from frappe.utils import time_diff_in_seconds, get_datetime

class SmartFM_ToDo(ToDo):
	def get_turn_off_reminder_url(self):
		user = frappe.session.user
		return get_reminder_off_url(self, user) 
	
	def after_insert(self):
		update_request(self, "Start")

	def validate(self):
		super().validate()
		if self.status == "Completed":
			update_request(self, "Resolve")
		
		self.set_navix_ticket()
		self.check_navix_ticket()

	def set_complete(self):
		self.status = "Completed"
		self.check_navix_ticket()
	
	def check_navix_ticket(self):
		if not self.navix_ticket:
			return
		
		# set time only once
		if self.status == "Planned" and self.start_working:
			return
		if self.status == "Completed" and self.end_working:
			return
		
		# custom calculation
		if self.reference_type == "Asset Repair":
			if self.status == "Planned":
				self.start_working = get_datetime(frappe.get_value(self.reference_type, self.reference_name, "failure_date"))
			elif self.status == "Completed":
				self.end_working = get_datetime(frappe.get_value(self.reference_type, self.reference_name, "completion_date"))
				self.working_time = time_diff_in_seconds(self.end_working, self.start_working)
		
		elif self.reference_type == "Asset Maintenance Log":
			if self.status == "Planned":
				self.start_working = get_datetime(frappe.get_value(self.reference_type, self.reference_name, "due_date"))
			elif self.status == "Completed":
				self.end_working = get_datetime(frappe.get_value(self.reference_type, self.reference_name, "completion_date"))
				self.working_time = time_diff_in_seconds(self.end_working, self.start_working)

		else:
			if self.status == "Planned":
				self.set_working_time(start=1) 
			elif self.status == "Completed":
				self.set_working_time(stop=1)

	def set_navix_ticket(self):
		if self.navix_ticket:
			return
		
		if self.reference_type in ("Asset Repair", "Asset Maintenance Log"):
			self.navix_ticket = 1

		
