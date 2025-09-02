# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime

ES_NAME="email_account.resync_email_inbox"
ER_NAME="erp.read_email_inbox"
NOTIF = "AI Agent Not Working"

class AIAgentSettings(Document):
	def validate(self):
		# detect old change
		self.detect_changed()

	@frappe.whitelist()
	def mark_complete(self, typ):
		mark_issue(typ, complete=1)
	
	def get_method(self, typ):
		if typ==1:
			return ES_NAME
		else:
			return ER_NAME
	
	def get_details(self, typ, field="details"):
		method = self.get_method(typ)
		log = frappe.db.get_value(
			"Scheduled Job Log",
			{"status": "Failed", "scheduled_job_type":method},
			["creation", "details"],
			order_by="creation desc",
			as_dict=1
		)
		if log:
			return log.get(field)
	
	def detect_changed(self):
		# detect changed
		old_doc = self.get_doc_before_save()
		if old_doc:
			if self.get("email_sync_issue") and not old_doc.get("email_sync_issue"):
				# checked
				self.send_notification(1)
			elif self.get("email_read_issue") and not old_doc.get("email_read_issue"):
				# checked
				self.send_notification(2)
			elif not self.get("email_sync_issue") and old_doc.get("email_sync_issue"):
				# unchecked
				self.send_notification(1, True)
			elif not self.get("email_read_issue") and old_doc.get("email_read_issue"):
				# unchecked
				self.send_notification(2, True)
		else:
			if self.get("email_sync_issue"):
				# checked
				self.send_notification(1)
			elif self.get("email_read_issue"):
				# checked
				self.send_notification(2)
			
	def send_notification(self, typ, complete=False):
		notif = frappe.get_doc("Notification", NOTIF)
		self.typ=typ
		if not complete:
			self.state = "🔴 Not working"
			self.issue = True
			notif.send(self)
		else:
			self.state = "🟢 Working"
			self.issue = False
			self.time = get_datetime()
			notif.send(self)

# send notification
def read_log(doc, method=""):
	if doc.status != 'Failed':
		return
	
	if doc.scheduled_job_type == ES_NAME:
		mark_issue(1, log=doc)

	elif doc.scheduled_job_type == ER_NAME:
		mark_issue(2, log=doc)
	
	else:
		return
	
def mark_issue(typ, complete=False, log=None):
	# 1 = ER
	# 2 = ES
	if typ == 1:
		field_check = "email_sync_issue"
		field_since = "es_since"
	elif typ == 2:
		field_check = "email_read_issue"
		field_since = "er_since"
	is_error = frappe.db.get_single_value("AI Agent Settings", field_check)
	if not complete:
		# mark error
		if not is_error:
			settings = frappe.get_doc("AI Agent Settings")
			settings.set(field_since, get_datetime(log.creation))
			settings.set(field_check, 1)
			settings.save()
	else:
		# mark complete
		if is_error:
			settings = frappe.get_doc("AI Agent Settings")
			settings.set(field_since, "")
			settings.set(field_check, 0)
			settings.save()

