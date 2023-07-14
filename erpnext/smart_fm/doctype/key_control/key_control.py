# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class KeyControl(Document):
	def autoname(self):
		self.name = make_autoname(self.name1[0:3].upper() + "-.#####") 

@frappe.whitelist()
def create_to_do(name):
	todo = frappe.new_doc("ToDo")
	todo.update({"reference_type": "Key Control", "reference_name": name})
	return todo
