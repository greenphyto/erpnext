# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

"""
Report for daily accumulation broker vs stock
"""

import frappe
from datetime import datetime
import calendar

def execute(filters=None):
	return Report(filters).execute()


def get_month_labels(year=2025):
    return [f"{calendar.month_abbr[i]}-{str(year)[-2:]}" for i in range(1, 13)]

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = " AND YEAR(si.posting_date) = %(year)s "

		if self.filters.get("customer"):
			self.cond += " AND si.customer = %(customer)s"
		if self.filters.get("item_code"):
			self.cond += " AND sii.item_code = %(item_code)s"

	def setup_column(self):
		columns = [
			{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
			{"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "width": 100, "options":"Item"},
			{"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180}
		]
		
		# Tambah kolom per bulan
		for m in get_month_labels():
			columns.append({
				"label": m, "fieldname": m.lower().replace('-', '_'), "fieldtype": "Float", "width": 90
			})

		# Tambah kolom total
		columns.append({
			"label": "Total", "fieldname": "total", "fieldtype": "Float", "width": 100
		})
		
		self.columns = columns
	
	def get_data(self):
		raw = frappe.db.sql("""
			SELECT
				si.customer,
				sii.item_name,
				sii.item_code,
				si.posting_date,
				sii.stock_qty as qty
			FROM
				`tabSales Invoice Item` sii
			JOIN
				`tabSales Invoice` si ON sii.parent = si.name
			JOIN
				`tabItem` i ON i.name = sii.item_code
			WHERE
				si.docstatus = 1
				AND i.is_stock_item = 1
				{}
		""".format(self.cond), self.filters, as_dict=1)

		# key = (customer, item)
		item_map = {}

		for row in raw:
			month_label = row.posting_date.strftime('%b-%y')
			field_key = month_label.lower().replace('-', '_')
			key = (row.customer, row.item_name)

			if key not in item_map:
				item_map[key] = {
					"customer": row.customer,
					"item_name": row.item_name,
					"item_code": row.item_code,
					"total": 0,
					**{m.lower().replace('-', '_'): 0 for m in get_month_labels()}
				}

			item_map[key][field_key] += row.qty
			item_map[key]["total"] += row.qty

		self.data = sorted(item_map.values(), key=lambda x: (x["customer"], x["item_name"]))
		# self.data = list(item_map.values())
	
	# def process_data(self):
	# 	self.data = self.raw_data

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		# self.process_data()

		return self.columns, self.data