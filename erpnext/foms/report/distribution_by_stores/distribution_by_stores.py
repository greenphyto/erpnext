# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import getdate
from datetime import timedelta

def execute(filters=None):
	print(10)
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = ""
		if self.filters.get("start_date") and self.filters.get("end_date"):
			self.cond += " and d.posting_date between %(start_date)s and %(end_date)s "

	def setup_column(self):
		self.columns = [
			{"fieldname": "outlet_name", 	"label": "Outlet Name", 	"fieldtype": "Data", "width":300, "options":""},
		]
		self.get_day_columns()

	def get_day_columns(self):
		start_date = getdate("2025-02-01")
		end_date = getdate("2025-02-28")
		
		column_map = {}
		columns = []

		current = start_date
		while current <= end_date:
			# Buat name dan label
			name = f"{current.day}_{current.strftime('%b').lower()}_{current.year % 100}"
			label = current.strftime('%d %b')

			column = frappe._dict({
				"range_start": current,
				"range_end": current,
				"label": label,
				"name": name
			})

			column_map[name] = column

			columns.append({
				"fieldname": name,
				"label": label,
				"fieldtype": "Float",
				"width": 100
			})

			current += timedelta(days=1)


		self.columns += columns
		self.column_map = column_map
		print(self.column_map)
		return columns, column_map

	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT 
				d.shipping_address_name,
				a.outlet_name,
				d.posting_date,
				di.item_code,
				di.parent AS delivery_note,
				COUNT(di.qty)
			FROM
				`tabDelivery Note Item` di
					LEFT JOIN
				`tabDelivery Note` d ON d.name = di.parent
					LEFT JOIN
				`tabAddress` a ON a.name = d.shipping_address_name
			WHERE
				di.docstatus = 1
					AND d.non_package_item = 0
					AND d.name LIKE 'DO-%%'
				{}
			GROUP BY d.shipping_address_name , di.item_code
		""".format(self.cond), self.filters, as_dict=1)

	def get_item_column_name(self, posting_date, item_code):
		item = item_code.split("-")[-1]
		date = getdate(posting_date)
		dt = f"{date.day}_{date.month}_{date.year % 100}"
		return f"{dt}_{item}"
	
	def process_data(self):
		self.data = []
		self.outle_map = {}
		items = []
		for d in self.raw_data:
			if d.outlet_name not in self.outle_map:
				self.outle_map[d.outlet_name] = [{

				}]
			else:
				self.outle_map[d.outlet_name].append({

				})


	def execute(self):
		print(78)
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data 