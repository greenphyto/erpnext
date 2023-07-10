# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AccessRequest(Document):
	pass

@frappe.whitelist()
def create_to_do():
	todo = frappe.new_doc("ToDo")
	return todo
