import frappe
from frappe.desk.doctype.todo.todo import ToDo
from erpnext.smart_fm.controllers.smart_fm import get_reminder_off_url

class SmartFM_ToDo(ToDo):
	def get_turn_off_reminder_url(self):
		user = frappe.session.user
		return get_reminder_off_url(self, user) 