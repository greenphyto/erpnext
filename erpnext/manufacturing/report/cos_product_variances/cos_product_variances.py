# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
import datetime

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
			{"fieldname": "prev_value", 		"label": "Prev. Values",	"fieldtype": "Currency", 	"width":100, "options":""}
			
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
		use_test= 1

		if not use_test:
			self.raw_data = frappe.db.sql("""
				SELECT 
					s.posting_date,
					s.name AS stock_entry,
					s.work_order,
					s.operation,
					si.expense_account,
					si.description,
					w.production_item as product,
					si.amount,
					si.cost_center,
					s.total_additional_costs,
					s.total_outgoing_value,
					s.total_outgoing_value - s.total_additional_costs AS raw_mat
				FROM
					`tabLanded Cost Taxes and Charges` si
						LEFT JOIN
					`tabStock Entry` s ON s.name = si.parent
						LEFT JOIN
					`tabWork Order` w ON w.name = s.work_order
				WHERE
					s.docstatus = 1
						AND s.purpose = 'Material Transfer for Manufacture'
						AND s.work_order = '24-014156-004'
				ORDER BY s.work_order , s.creation
			""".format(self.cond), self.filters, as_dict=1)
		else:
			self.raw_data = get_test_data()
	
	def process_data(self):
		self.data = []

		temp_data = []
		data_mapping = {}
		wo_mapping = {}
		cur_key = ""
		for d in self.raw_data:
			if d.work_order not in data_mapping:
				data_mapping[d.work_order] = {
					"Seeding": {
						"costs":0,
						"rawmat":0,
						'row':{}
					},
					"Transplanting": {
						"costs":0,
						"rawmat":0,
						'row':{}
					},
					"Harvesting": {
						"costs":0,
						"rawmat":0,
						'row':{}
					},
				}
			
			row = d
			data_mapping[d.work_order][d.operation]["rawmat"] = d.raw_mat
			if not data_mapping[d.work_order][d.operation]['row']:
				data_mapping[d.work_order][d.operation]['row'] = d

			for c in self.cost_type:
				cost_name = f"{c} Cost"
				if cost_name == d.description:
					field = self.get_cost_column_field(c)
					data_mapping[d.work_order][d.operation]['row'][field] = flt(data_mapping[d.work_order][d.operation]['row'].get(field)) + flt(d.amount)
					data_mapping[d.work_order][d.operation]["costs"] += data_mapping[d.work_order][d.operation]['row'][field]

		for wo, values in data_mapping.items():
			for opr, dt in values.items():
				d = dt['row']
				if d.operation == "Seeding":
					d['credit'] = data_mapping[d.work_order]['Seeding']["costs"]
					d['prev_value'] = 0
				elif d.operation == "Transplanting":
					d['credit'] = ( 
						data_mapping[d.work_order]['Seeding']["costs"] +
						data_mapping[d.work_order]['Seeding']["rawmat"] + 
						data_mapping[d.work_order]['Transplanting']["costs"] 
					)
					d['prev_value'] = ( 
						data_mapping[d.work_order]['Seeding']["costs"] +
						data_mapping[d.work_order]['Seeding']["rawmat"] 
					)
				elif d.operation == "Harvesting":
					d['credit'] = ( 
						data_mapping[d.work_order]['Seeding']["costs"] +
						data_mapping[d.work_order]['Seeding']["rawmat"] + 
						data_mapping[d.work_order]['Transplanting']["costs"] +
						data_mapping[d.work_order]['Transplanting']["rawmat"] +
						data_mapping[d.work_order]['Harvesting']["costs"] 
					)
					d['prev_value'] = ( 
						data_mapping[d.work_order]['Seeding']["costs"] +
						data_mapping[d.work_order]['Seeding']["rawmat"] + 
						data_mapping[d.work_order]['Transplanting']["costs"] +
						data_mapping[d.work_order]['Transplanting']["rawmat"]
					)
				
				self.data.append(d)

	
	def get_cost_column_field(self, cost_type):
		return cost_type.lower()

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data


TEST_DATA = [
{'posting_date': datetime.date(2024, 10, 23), 'stock_entry': 'SE-00009/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Seeding', 		'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Electrical Cost', 	'amount': 0, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 4, 'total_outgoing_value': 10, 'raw_mat': 6},
{'posting_date': datetime.date(2024, 10, 23), 'stock_entry': 'SE-00009/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Seeding', 		'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Machinery Cost', 	'amount': 2, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 4, 'total_outgoing_value': 10, 'raw_mat': 6},
{'posting_date': datetime.date(2024, 10, 23), 'stock_entry': 'SE-00009/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Seeding', 		'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Consumable Cost', 	'amount': 0, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 4, 'total_outgoing_value': 10, 'raw_mat': 6},
{'posting_date': datetime.date(2024, 10, 23), 'stock_entry': 'SE-00009/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Seeding', 		'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Wages Cost', 		'amount': 2, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 4, 'total_outgoing_value': 10, 'raw_mat': 6},
{'posting_date': datetime.date(2024, 10, 25), 'stock_entry': 'TR-00005/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Transplanting', 	'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Electrical Cost', 	'amount': 0, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 2, 'total_outgoing_value': 6, 'raw_mat': 4},
{'posting_date': datetime.date(2024, 10, 25), 'stock_entry': 'TR-00005/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Transplanting', 	'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Wages Cost', 		'amount': 1, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 2, 'total_outgoing_value': 6, 'raw_mat': 4},
{'posting_date': datetime.date(2024, 10, 25), 'stock_entry': 'TR-00005/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Transplanting', 	'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Consumable Cost', 	'amount': 0, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 2, 'total_outgoing_value': 6, 'raw_mat': 4},
{'posting_date': datetime.date(2024, 10, 25), 'stock_entry': 'TR-00005/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Transplanting', 	'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Machinery Cost', 	'amount': 1, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 2, 'total_outgoing_value': 6, 'raw_mat': 4},
{'posting_date': datetime.date(2024, 10, 25), 'stock_entry': 'HR-00008/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Harvesting', 	'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Consumable Cost', 	'amount': 0, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 1, 'total_outgoing_value': 2, 'raw_mat': 1},
{'posting_date': datetime.date(2024, 10, 25), 'stock_entry': 'HR-00008/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Harvesting', 	'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Machinery Cost', 	'amount': 0, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 1, 'total_outgoing_value': 2, 'raw_mat': 1},
{'posting_date': datetime.date(2024, 10, 25), 'stock_entry': 'HR-00008/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Harvesting', 	'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Electrical Cost', 	'amount': 0, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 1, 'total_outgoing_value': 2, 'raw_mat': 1},
{'posting_date': datetime.date(2024, 10, 25), 'stock_entry': 'HR-00008/2024', 'work_order': '24-014156-004',"product":"PR-AV-SPC", 'operation': 'Harvesting', 	'expense_account': '540000 - COS Prod Variance - GPL', 'description': 'Wages Cost', 		'amount': 1, 'cost_center': '4020 - Packing - GPL', 'total_additional_costs': 1, 'total_outgoing_value': 2, 'raw_mat': 1}
]

def get_test_data():
	res = []
	for d in TEST_DATA:
		res.append(frappe._dict(d))
	
	return res