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

	def setup_column(self):
		self.columns = [
			{"fieldname": "batch_no", 		"label": "Batch No", 	"fieldtype": "Link", "width":160, "options":"Batch"},
			{"fieldname": "item_code", 		"label": "Item", 		"fieldtype": "Data", "width":200, "options":""},
			{"fieldname": "expiry_date", 	"label": "Exp. Date", 	"fieldtype": "Date", "width":100, "options":""},
			{"fieldname": "prod_qty", 		"label": "Qty Prod", 	"fieldtype": "Float", "width":80, "options":""},
			{"fieldname": "delivery_note",	"label": "DO No", 		"fieldtype": "Link", "width":150, "options":"Delivery Note"},
			{"fieldname": "delivery_date", 	"label": "Deliv. Date", "fieldtype": "Date", "width":100, "options":""},
			{"fieldname": "qty", 			"label": "Qty Sent", 	"fieldtype": "Float", "width":80, "options":""},
			{"fieldname": "uom", 			"label": "UOM", 		"fieldtype": "Data", "width":130, "options":""},
			{"fieldname": "customer", 		"label": "Customer", 	"fieldtype": "Link", "width":220, "options":"Customer"},
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT 
				b.name AS batch_no,
				b.item_name as item_code,
				b.expiry_date,
				d.name AS delivery_note,
				d.posting_date as delivery_date,
				d.customer,
								i.uom,
				i.qty
			FROM
				tabBatch AS b
					LEFT JOIN
				`tabDelivery Note Item` i ON i.batch_no = b.name
					LEFT JOIN
				`tabDelivery Note` d ON d.name = i.parent
			WHERE
				i.docstatus = 1
					AND i.batch_no IS NOT NULL
			ORDER BY b.expiry_date DESC , i.batch_no
		""".format(self.cond), self.filters, as_dict=1)
	
	def process_data(self):
		self.data = []
		added = []
		for d in self.raw_data:
			if d.batch_no in added:
				d.batch_no = ""
				d.item_code = ""
				d.expiry_date = ""
				self.data.append(d)
				continue

			added.append(d.batch_no)
			self.data.append(d)

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data