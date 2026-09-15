# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = ""

	def setup_column(self):
		self.columns = [
			{"fieldname": "work_order", 		"label": "Work Order", 		"fieldtype": "Link", 	 "width":120, "options":"Work Order"},
			{"fieldname": "plan_cost", 			"label": "Planned Cost", 	"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "actual_cost", 		"label": "Actual Cost", 	"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "cost_variance", 		"label": "Cost Variance", 	"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "material_cost", 		"label": "Materials Cost", 	"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "labor_cost", 		"label": "Labor Cost", 		"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "overhead_cost", 		"label": "Overhead Cost", 	"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "additional_cost", 	"label": "Additional Costs","fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "qty", 				"label": "Prod. Quantity", 	"fieldtype": "Float",    "width":120, "options":""},
			{"fieldname": "status", 			"label": "Status", 			"fieldtype": "Data",     "width":120, "options":""},
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			select * from `tabWork Order`
		""".format(self.cond), self.filters, as_dict=1)
	
	def process_data(self):
		self.data = self.raw_data

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data