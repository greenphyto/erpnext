# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint

class Packaging(Document):
	def validate(self):
		self.create_uom_packaging()
		self.enable_disable()

	def after_rename(self, old, new, merge):
		self.sync_new_name(old, new)

	def on_trash(self):
		self.delete_uom_packaging()

	def create_uom_packaging(self):
		if self.get_uom_name():
			return
	
		doc = frappe.new_doc("UOM")
		doc.is_packaging = 1
		doc.must_be_whole_number = 1
		doc.uom_name = self.name
		doc.insert(ignore_permissions=1)

	def get_uom_name(self, name=None):
		uom = name or self.name
		return frappe.get_value("UOM", uom)

	def delete_uom_packaging(self):
		exists = self.get_uom_name()
		if not exists:
			return
	
		frappe.delete_doc("UOM", exists)

	def enable_disable(self):
		exists = self.get_uom_name()
		if not exists:
			return
		
		if cint(self.disable):
			frappe.db.set_value("UOM", exists, "enabled", 0)
		else:
			frappe.db.set_value("UOM", exists, "enabled", 1)

	def sync_new_name(self, old, new):
		exists = self.get_uom_name(old)
		if not exists:
			return
		
		frappe.rename_doc("UOM", exists, self.name, force=1)
