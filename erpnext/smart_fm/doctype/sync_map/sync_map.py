# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document

class SyncMap(Document):
	pass

def get_sync_map(origin_doctype, origin_name, method_name):
	exists = frappe.db.exists("Sync Map", {
		"origin_doctype":origin_doctype, 
		"origin_name":origin_name,
		"method_name": method_name
	})
	if not exists:
		return 
	else:
		return frappe.get_doc("Sync Map", exists)
	
def create_sync_map(source, result, method_name):
	doc = frappe.new_doc("Sync Map")
	doc.origin_doctype = source.doctype
	doc.origin_name = source.name
	doc.destination_doctype = result.doctype
	doc.destination_name = result.name
	doc.method_name = method_name
	doc.last_sync = now()
	doc.insert(ignore_permissions=1)