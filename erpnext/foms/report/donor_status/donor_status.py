# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

"""
Report for daily accumulation broker vs stock
"""

import frappe

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = ""
		if self.filters.get('from_date') and self.filters.get('to_date'):
			self.cond += " and so.transaction_date between '{}' and '{}'".format(self.filters['from_date'], self.filters['to_date'])
		if self.filters.get('sales_order'):
			self.cond += " and so.name = '{}'".format(self.filters['sales_order'])
		if self.filters.get('branch'):
			self.cond += " and so.donor_name like '{}'".format("%{}%".format(self.filters['branch']))

	def setup_column(self):
		self.unique_items = []
		seen = set()
		for row in self.raw_data:
			if row['item_code'] not in seen:
				seen.add(row['item_code'])
				self.unique_items.append({
					'item_code': row['item_code'],
					'item_name': row['item_name']
				})

		self.columns = [
			{"fieldname": "sales_order",     "label": "SO#",        "fieldtype": "Link",  "width": 140, "options": "Sales Order"},
			{"fieldname": "transaction_date","label": "Date",        "fieldtype": "Date",  "width": 100},
			{"fieldname": "donor_name",      "label": "Donor",       "fieldtype": "Data",  "width": 150},
			{"fieldname": "status",      	"label": "Status",       "fieldtype": "Data",  "width": 120},
		]

		# Dynamic kolom per item
		for item in self.unique_items:
			fieldname = frappe.scrub(item['item_code'])  # jadi snake_case aman
			self.columns.append({
				"fieldname": fieldname,
				"label": item['item_name'],
				"fieldtype": "Float",
				"width": 120
			})

		self.columns += [
			{"fieldname": "total_qty",      "label": "Total Qty",     "fieldtype": "Float", "width": 100},
			{"fieldname": "delivered_qty",  "label": "Delivered Qty", "fieldtype": "Float", "width": 120},
			{"fieldname": "balance",        "label": "Balance",       "fieldtype": "Float", "width": 100},
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT
				so.name AS sales_order,
				so.transaction_date,
				so.donor_name,
				so.status,
				soi.item_code,
				soi.item_name,
				soi.qty AS total_qty,
				soi.delivered_qty,
				(soi.qty - soi.delivered_qty) AS balance
			FROM
				`tabSales Order` so
			INNER JOIN
				`tabSales Order Item` soi ON soi.parent = so.name
			WHERE
				so.is_pledge = 1
				AND so.docstatus = 1
				{}
			ORDER BY
				so.transaction_date DESC
		""".format(self.cond), as_dict=1, debug=0)
	
	def process_data(self):
		grouped = {}
		for row in self.raw_data:
			key = row['sales_order']
			if key not in grouped:
				grouped[key] = {
					'sales_order': row['sales_order'],
					'transaction_date': row['transaction_date'],
					'donor_name': row['donor_name'],
					'total_qty': 0,
					'delivered_qty': 0,
					'balance': 0,
					'status': row['status'],
					**{frappe.scrub(item['item_code']): 0 for item in self.unique_items}
				}
			
			fieldname = frappe.scrub(row['item_code'])
			grouped[key][fieldname] = row['total_qty']
			grouped[key]['total_qty'] += row['total_qty']
			grouped[key]['delivered_qty'] += row['delivered_qty']
			grouped[key]['balance'] += row['balance']

		self.data = list(grouped.values())

	def execute(self):
		self.setup_condition()
		self.get_data()
		self.setup_column()
		self.process_data()

		return self.columns, self.data