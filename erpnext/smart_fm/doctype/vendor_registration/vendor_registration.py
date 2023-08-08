# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class VendorRegistration(Document):
	def validate(self):
		self.create_supplier()

	def create_supplier(self, force=False):
		old_doc = self.get_doc_before_save()
		def _create_supplier():
			supplier_group = frappe.db.get_single_value("Smart FM Settings", "default_supplier_group")
			data = {
				'supplier_name': self.company_name,
				'website': self.company_website,
				'supplier_group': supplier_group
			}
			exists = frappe.db.exists("Supplier", data)
			if not exists:
				doc = frappe.new_doc("Supplier")
				doc.update(data)
				doc.insert(ignore_permissions=True)

			# create contact
			# create address
			
		if old_doc and old_doc.get("workflow_state") != self.workflow_state and self.workflow_state == "Approved" or force:
			_create_supplier()

		

@frappe.whitelist()
def create_to_do(name):
	todo = frappe.new_doc("ToDo")
	todo.update({"reference_type": "Vendor Registration", "reference_name": name})
	return todo