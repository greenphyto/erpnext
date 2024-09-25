# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr

class PartNumberSettings(Document):
	@frappe.whitelist()
	def load_items(self):
		items = frappe.db.sql('select * from `tabItem` where material_group is not null and material_group != "" order by material_group, material_number', as_dict=1)
		data_mapping = list(self.data_mapping)
		mat_groups = frappe.db.sql(' select * from `tabMaterial Group` order by number_start ', as_dict=1)

		cur_item = {}
		for d in items:
			cur_item[cstr(d.material_number)] = d
		
		set_item = {}
		for d in data_mapping:
			set_item[cstr(d.part_number)] = d

		limit = 200

		data = []
		self.data_mapping = []
		for d in mat_groups:
			cur_index = 0
			start_index = cint(d.number_start)
			for i in range(limit):
				key = cstr(start_index + i)
				dt = set_item.get(key)
				if dt:
					# from settings
					self.data_mapping.append(dt)
					continue

				if not dt:
					dt = cur_item.get(key)

				if dt:
					# from items
					row = self.append("data_mapping")
					row.material_group = dt.material_group
					row.code = dt.item_code
					row.part_number = dt.material_number
					row.title = dt.item_name
					row.price = d.price_control
					row.start = d.number_start
					row.end = d.number_end