# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.smart_fm.controllers.firebase import FirebaseNotification
class FirebaseNotificationSettings(Document):
	pass

@frappe.whitelist()
def send_message(message, user):
	notif = FirebaseNotification()
	token = frappe.get_value("Firebase User Token", {"user":user}, "token") 
	if token:
		notif.send_message(message, token)
		return True
	
	return False