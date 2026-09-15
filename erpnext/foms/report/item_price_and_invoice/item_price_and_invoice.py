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
		if self.filters.get("item_code"):
			self.cond += (" and sii.item_code = %(item_code)s ")
		if self.filters.get("customer"):
			self.cond += (" and icr.customer = %(customer)s ")
		if self.filters.get("invoice"):
			self.cond += (" and si.name = %(batch_no)s ")

	def setup_column(self):
		self.columns = [
			{"fieldname": "item_code", 		"label": "Item", 		"fieldtype": "Link", 	"options": "Item", "width": 130},
			{"fieldname": "uom", 			"label": "UOM", 		"fieldtype": "Link", 	"options": "UOM", "width": 200},
			{"fieldname": "customer", 		"label": "Customer",	"fieldtype": "Link", 	"options": "Customer", "width": 250},
			{"fieldname": "mapped_rate", 	"label": "Cust. Rate", "fieldtype": "Currency", "width": 120},
			{"fieldname": "invoice_rate", 	"label": "Inv. Rate","fieldtype": "Currency", "width": 120},
			{"fieldname": "rate_difference","label": "Difference", 		"fieldtype": "Currency", "width": 100},
			{"fieldname": "sales_invoice", 	"label": "Sales Invoice","fieldtype": "Link", 	"options": "Sales Invoice", "width": 140},
			{"fieldname": "posting_date", 	"label": "Posting Date","fieldtype": "Date", 	"options": "", "width": 120},
		]

	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT
				sii.item_code,
				sii.uom,
				si.customer,
				sii.rate AS invoice_rate,
				icr.rate AS mapped_rate,
				(sii.rate - icr.rate) AS rate_difference,
				si.name AS sales_invoice,
				si.posting_date
			FROM
				`tabSales Invoice Item` sii
			JOIN
				`tabSales Invoice` si ON sii.parent = si.name
			LEFT JOIN
				`tabItem Customer Price` icr ON
					icr.parent = sii.item_code
					AND icr.customer = si.customer
					AND icr.uom = sii.uom
			LEFT JOIN
				`tabItem` i on i.name = sii.item_code
			WHERE
				si.docstatus = 1 
				and i.item_group = "Products"
				and si.is_return = 0
				{}
			ORDER BY
				si.posting_date DESC, si.name;

		""".format(self.cond), self.filters, as_dict=1)
	
	def process_data(self):
		self.data = self.raw_data

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data