# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime
class AIAgentSettings(Document):
	@frappe.whitelist()
	def mark_complete(self, typ):
		mark_issue(typ, complete=1)


ES_NAME="email_account.resync_email_inbox"
ER_NAME="erp.read_email_inbox"

# send notification
def read_log(doc, method=""):
	if doc.status != 'Failed':
		return
	
	if doc.scheduled_job_type == ES_NAME:
		mark_issue(2, log=doc)

	elif doc.scheduled_job_type == ER_NAME:
		mark_issue(1, log=doc)
	
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

