# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint
from frappe import _
from frappe.model.document import Document

class MaterialGroup(Document):
	def onload(self):
		self.check_exist_item()

	def validate(self):
		self.validate_number_range()
		self.validate_number_exists()

	def validate_number_range(self):
		if cint(self.number_end) < cint(self.number_start):
			frappe.throw(_("Number end must be grater than start"))
	
	def validate_number_exists(self):
		filters = [
			{
				"number_start":['between', [self.number_start, self.number_end]],
				"name":['!=', self.name]
			},
			{
				"number_end":['between', [self.number_start, self.number_end]],
				"name":['!=', self.name]
			},
			{
				"number_start":['>=', self.number_start],
				"number_end":['<=', self.number_end],
				"name":['!=', self.name]
			},
			{
				"number_start":['<=', self.number_start],
				"number_end":['>=', self.number_end],
				"name":['!=', self.name]
			},
		]

		for f in filters:
			exist = frappe.db.get_value("Material Group", f, ['material_group_name','number_start', 'number_end' ], as_dict=1)

			if exist:
				frappe.throw(_(f"overlapping number range with <b>{exist.material_group_name}</b> ({exist.number_start}-{exist.number_end})"))

	def check_exist_item(self):
		exist = frappe.get_value("Item", {"material_group":self.name})
		if exist:
			self.set_onload("exist_transaction", True)
		else:
			self.set_onload("exist_transaction", False)
