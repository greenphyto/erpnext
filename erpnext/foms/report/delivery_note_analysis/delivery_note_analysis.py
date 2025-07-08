# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
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
			{"fieldname": "broker", 	"label": "Broker", 	"fieldtype": "Link", "width":120, "options":"Broker"},
			{"fieldname": "stock", 		"label": "Stock", 	"fieldtype": "Link", "width":120, "options":"Emiten"},
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			select * from `tabBroker Activity`
		""".format(self.cond), self.filters, as_dict=1)
	
	def process_data(self):
		self.data = self.raw_data

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data
