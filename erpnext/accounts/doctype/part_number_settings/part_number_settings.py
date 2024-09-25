# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr
from erpnext.accounts.utils import get_balance_on

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
		idx = 1
		for d in mat_groups:
			cur_index = 0
			start_index = cint(d.number_start)
			for i in range(limit):
				key = cstr(start_index + i)
				dt = set_item.get(key)
				if dt:
					# from settings
					dt.idx = idx
					row = self.append("data_mapping")
					row.update(dt.as_dict())
					idx += 1
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
					row.idx = idx
					idx += 1

	def validate(self):
		self.validate_account_change()

	def validate_account_change(self):
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return

		old_map = {}
		for d in old_doc.data_mapping:
			old_map[d.part_number] = d
		
		for d in self.data_mapping:
			old_data = old_map.get(d.part_number)
			if not old_data:
				continue

			if old_data.account_code and old_data.account_code != d.account_code:
				balance = get_balance_on(old_data.account_code)
				if balance:
					frappe.throw(f"Row {d.idx}, Cannot change account <b>{old_data.account_code}</b> to {d.account_code} becuase has existing balance")
					d.account_code = old_data.account_code
