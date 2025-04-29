# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import flt

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = ""

	def setup_column(self):
		self.columns = [
			{"fieldname": "posting_date", 	"label": "Date", 		"fieldtype": "Date", 	"width":120, "options":""},
			{"fieldname": "sales_invoice", 	"label": "Invoice No", 	"fieldtype": "Link", 	"width":120, "options":"Sales Invoice"},
			{"fieldname": "customer", 		"label": "Customer", 	"fieldtype": "Link", 	"width":220, "options":"Customer"},
			{"fieldname": "outlet_name", 	"label": "Store Name", 	"fieldtype": "Data", 	"width":120, "options":""},
			{"fieldname": "item_code", 		"label": "Item", 		"fieldtype": "Link", 	"width":120, "options":"Item"},
			{"fieldname": "qty", 			"label": "Qty", 		"fieldtype": "Float", 	"width":80, "options":""},
			{"fieldname": "uom", 			"label": "UOM", 		"fieldtype": "Link", 	"width":180, "options":"UOM"},
			{"fieldname": "rate", 			"label": "Price", 		"fieldtype": "Currency", "width":100, "options":""},
			{"fieldname": "amount", 		"label": "Amount", 		"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "gst", 			"label": "GST", 		"fieldtype": "Percent", "width":100, "options":""},
			{"fieldname": "gst_amount", 	"label": "GST Amount", 	"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "total_amount", 	"label": "Total Amount","fieldtype": "Currency", "width":120, "options":""},
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT 
				s.posting_date,
				s.name AS sales_invoice,
				s.customer,
				s.total,
				a.outlet_name,
				si.item_code,
				si.qty,
				si.item_tax_rate,
				si.rate,
				si.uom,
				si.amount,
				si.net_amount,
				t.name AS tx_row,
				t.charge_type,
				t.rate as gst,
				t.tax_amount as gst_amount
			FROM
				`tabSales Invoice` s
					LEFT JOIN
				`tabSales Invoice Item` si ON si.parent = s.name
					LEFT JOIN
				`tabSales Taxes and Charges` t ON t.parent = s.name
					left join
				`tabAddress` a on a.name = s.shipping_address_name
			ORDER BY s.posting_date desc
		""".format(self.cond), self.filters, as_dict=1)
	
	def process_data(self):
		self.data = []
		for d in self.raw_data:
			# calculate tax amount
			if d.total:
				d.gst_amount = flt(d.amount)/flt(d.total)*flt(d.gst_amount)
				d.total_amount = d.gst_amount + flt(d.amount)

			self.data.append(d)

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data