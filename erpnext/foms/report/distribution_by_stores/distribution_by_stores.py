# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import getdate, flt
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
			{"fieldname": "index", 			"label": "No", 	"fieldtype": "Int", "width":50, "options":""},
			{"fieldname": "outlet_name", 	"label": "Outlet Name", 	"fieldtype": "Data", "width":250, "options":""},
		]
		if self.filters.get("show_customer"):
			self.columns += [
				{"fieldname": "customer", 	"label": "Customer", 	"fieldtype": "Link", "width":250, "options":"Customer"}
			]
		self.get_day_columns()


	def get_day_columns(self):
		start_date = getdate(self.filters.start_date)
		end_date = getdate(self.filters.end_date)
		
		column_map = {}
		columns = []

		current = start_date
		nd_col = {"outlet_column":""}
		while current <= end_date:
			# Buat name dan label
			label = current.strftime('%d %b')

			for item in self.items:
				name = self.get_item_column_name(current, item)
				nd_col[name] = item.split("-")[-1]
				columns.append({
					"fieldname": name,
					"label": label,
					"fieldtype": "Int",
					"width": 110
				})
				label = ''

			current += timedelta(days=1)

		self.data.append(nd_col)
		self.columns += columns
		self.column_map = column_map
		return columns, column_map

	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT 
				d.shipping_address_name,
				a.outlet_name,
				d.customer,
				d.posting_date,
				di.item_code,
				di.parent AS delivery_note,
				di.qty
			FROM
				`tabDelivery Note Item` di
					LEFT JOIN
				`tabDelivery Note` d ON d.name = di.parent
					LEFT JOIN
				`tabAddress` a ON a.name = d.shipping_address_name
			WHERE
				di.docstatus = 1
					AND d.non_package_item = 0
					AND d.is_return = 0
					AND d.is_replacement = 0
					AND d.is_donation = 0
					AND d.is_giveaway = 0
				{}

		""".format(self.cond), self.filters, as_dict=1)

	def get_item_column_name(self, posting_date, item_code):
		item = frappe.scrub(item_code)
		date = getdate(posting_date)
		dt = f"{date.day}_{date.month}_{date.year % 100}"
		return f"{dt}_{item}"
	
	def process_data(self):
		self.data = []
		self.outlet_map = {}
		items = []
		for d in self.raw_data:
			col_name = self.get_item_column_name(d.posting_date, d.item_code)
			if d.outlet_name not in self.outlet_map:
				dt = {"outlet_name":d.outlet_name, "customer":d.customer}
				self.outlet_map[d.outlet_name] = dt
			self.outlet_map[d.outlet_name][col_name] = d.qty + flt(self.outlet_map[d.outlet_name].get(col_name))

			if d.item_code not in items:
				items.append(d.item_code)

		self.items = items

	def post_data(self):
		idx = 0
		for key, val in self.outlet_map.items():
			idx += 1
			val['index'] = idx
			self.data.append(val)

	def execute(self):
		self.setup_condition()
		self.get_data()
		self.process_data()
		
		self.setup_column()
		self.post_data()

		return self.columns, self.data 