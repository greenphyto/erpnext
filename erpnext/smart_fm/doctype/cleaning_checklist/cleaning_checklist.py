# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr, getdate
from erpnext.accounts.utils import get_fiscal_year

class CleaningChecklist(Document):
	def validate(self):
		self.add_user_name()
		self.set_period()
		self.set_status()

	def set_period(self):
		date_obj = getdate(self.posting_date, "%d-%m-%Y")
		month = date_obj.strftime("%B")  # Nama bulan
		year = get_fiscal_year(date = date_obj)[0]   # Tahun
		self.month = month
		self.year = year

	def add_user_name(self):
		full_name = frappe.db.get_value("User", frappe.session.user, "full_name")
		self.cleaned_by = full_name

	def get_template_area(self):
		data = frappe.db.sql("""
			SELECT 
				area, priority, level_1, level_2, level_3, level_4, level_5
			FROM
				`tabCleaning Area`
			ORDER BY priority		
		""",as_dict=1)
		map_level = {}
		for i in range(1,6):
			level = get_level_name(i)
			map_level[level] = []
			for d in data:
				if d.get(level):
					map_level[level].append(d)

		return map_level

	def set_status(self):
		if self.docstatus == 1:
			self.status = "Cleaned"

	@frappe.whitelist()
	def load_area(self, level):
		map_area = self.get_template_area()
		level_name = get_level_name(level)
		table_field = level_name + "_area"
		if not self.get(table_field):
			self.set(table_field, [])
			areas = map_area[level_name]
			for d in areas:
				row = self.append(table_field)
				row.area = d.area

def get_level_name(idx):
	return "level_"+cstr(cint(idx))

def get_level_index(level):
	return cint(level.repalce("level_"))