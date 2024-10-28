# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters
		self.cost_type = ["Electrical", "Consumable", "Machinery", "Wages"]

	def setup_condition(self):
		self.cond = ""

	def setup_column(self):
		self.columns = [
			{"fieldname": "posting_date", 		"label": "Posting Date", 	"fieldtype": "Date", 		"width":100, "options":""},
			{"fieldname": "stock_entry", 		"label": "Stock Entry", 	"fieldtype": "Link", 		"width":140, "options":"Stock Entry"},
			{"fieldname": "work_order", 		"label": "Work Order", 		"fieldtype": "Link", 		"width":140, "options":"Work Order"},
			{"fieldname": "product", 			"label": "Product", 		"fieldtype": "Link", 		"width":120, "options":"Item"},
			{"fieldname": "operation", 			"label": "Operation", 		"fieldtype": "Data", 		"width":120, "options":""},
			{"fieldname": "debit", 				"label": "Debit", 			"fieldtype": "Currency", 	"width":100, "options":""},
			{"fieldname": "credit", 			"label": "Credit", 			"fieldtype": "Currency", 	"width":100, "options":""},
			{"fieldname": "raw_mat", 			"label": "Raw. Materials",	"fieldtype": "Currency", 	"width":120, "options":""},
			{"fieldname": "packing", 			"label": "Packing", 		"fieldtype": "Currency",    "width":90, "options":""},
			
		]
		for c in self.cost_type:

			col = {
				"fieldname": self.get_cost_column_field(c), 			
				"label": c, 		
				"fieldtype": "Currency",    
				"width":90, 
			}
			self.columns.append(col)
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT 
				s.posting_date,
				s.name AS stock_entry,
				s.work_order,
				s.operation,
				si.expense_account,
				si.description,
				si.amount,
				si.cost_center,
				s.total_additional_costs,
				s.total_outgoing_value,
				s.total_outgoing_value - s.total_additional_costs as raw_mat
			FROM
				`tabLanded Cost Taxes and Charges` si
					LEFT JOIN
				`tabStock Entry` s ON s.name = si.parent
			WHERE
				s.docstatus = 1
					AND s.purpose = 'Material Transfer for Manufacture'
					and s.work_order = '24-014156-004'
			order by s.work_order, s.creation
		""".format(self.cond), self.filters, as_dict=1)
	
	def process_data(self):
		self.data = []

		data_mapping = {}
		cur_key = ""
		for d in self.raw_data:
			key = (d.operation, d.work_order)
			if key not in data_mapping:
				row = d
			else:
				row = data_mapping[key]

			row.credit = flt(row.get("credit")) + d.total_additional_costs
			for c in self.cost_type:
				cost_name = f"{c} Cost"
				if cost_name == d.description:
					field = self.get_cost_column_field(c)
					row[field] = flt(row.get(field)) + flt(d.amount)

			row.credit = flt(row.get("credit")) + d.total_additional_costs

			if not cur_key:
				cur_key = key
			elif cur_key != key:
				data_mapping[key] = row
				cur_key = ""
				print(92, "append", row)
		
			print(90, key, cur_key, row.credit, d.total_additional_costs)
		
		print(92, "append", row)
		data_mapping[key] = row

		for key, val in data_mapping.items():
			self.data.append(val)
	
	def get_cost_column_field(self, cost_type):
		return cost_type.lower()

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data