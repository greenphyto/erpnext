import frappe
from frappe.desk.doctype.todo.todo import ToDo
from erpnext.smart_fm.controllers.web_access import get_reminder_off_url
from erpnext.smart_fm.controllers.smart_fm import update_request

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
