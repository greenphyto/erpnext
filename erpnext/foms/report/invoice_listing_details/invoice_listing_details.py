# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import flt, cint
import datetime
import calendar

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = ""
		self.cond_delete = ""
		self.cond_all = ""

		if self.filters.get("customer"):
			self.cond += " and s.customer = %(customer)s "
		if self.filters.get("sales_invoice"):
			self.cond += " and s.name = %(sales_invoice)s "
		if self.filters.get("show_missing_invoice"):
			self.cond_all += " and c.sales_invoice is null "

		today = datetime.date.today()
		first_day = today.replace(day=1)
		last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
		self.filters.start_date = self.filters.get("start_date") or first_day
		self.filters.end_date = self.filters.get("end_date") or last_day
		self.cond += " and dn.posting_date between %(start_date)s and %(end_date)s "
		self.cond_delete += " and dd.document_date between %(start_date)s and %(end_date)s "

		if cint(self.filters.get("show_credit_note")):
			self.cond += " and s.is_return = 1 "

	def setup_column(self):
		self.columns = [
			{"fieldname": "posting_date", 	"label": "Deliv. Date", "fieldtype": "Date", 	"width":120, "options":""},
			{"fieldname": "sales_invoice", 	"label": "Invoice No", 	"fieldtype": "Link", 	"width":120, "options":"Sales Invoice"},
			{"fieldname": "status", 		"label": "Status", 		"fieldtype": "Data", 	"width":80, "options":""},
			{"fieldname": "customer", 		"label": "Customer", 	"fieldtype": "Link", 	"width":220, "options":"Customer"},
			{"fieldname": "outlet_name", 	"label": "Store Name", 	"fieldtype": "Data", 	"width":180, "options":""},
			{"fieldname": "delivery_note", 	"label": "Delivery Note","fieldtype": "Link", 	"width":140, "options":"Delivery Note"},
			{"fieldname": "delivery_date", 	"label": "Delivery Date","fieldtype": "Date", 	"width":120, "options":""},
			{"fieldname": "item_code", 		"label": "Item", 		"fieldtype": "Link", 	"width":100, "options":"Item"},
			{"fieldname": "qty", 			"label": "Qty", 		"fieldtype": "Float", 	"width":80, "options":""},
			{"fieldname": "uom", 			"label": "UOM", 		"fieldtype": "Link", 	"width":180, "options":"UOM"},
			{"fieldname": "weight", 		"label": "Weight (KG)", "fieldtype": "Float", 	"width":100, "options":""},
			{"fieldname": "cos", 			"label": "COS", 		"fieldtype": "Currency", "width":100, "options":""},
			{"fieldname": "rate", 			"label": "Price", 		"fieldtype": "Currency", "width":100, "options":""},
			{"fieldname": "amount", 		"label": "Amount", 		"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "gst", 			"label": "GST", 		"fieldtype": "Percent", "width":100, "options":""},
			{"fieldname": "gst_amount", 	"label": "GST Amount", 	"fieldtype": "Currency", "width":120, "options":""},
			{"fieldname": "total_amount", 	"label": "Total Amount","fieldtype": "Currency", "width":120, "options":""},
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT 
				c.*
			FROM
				(SELECT 
					dn.posting_date,
						s.name AS sales_invoice,
						IF(s.docstatus, 'Submit', 'None') AS status,
						dn.customer,
						s.total,
						a.outlet_name,
						dni.item_code,
						dni.qty,
						si.item_tax_rate,
						si.rate,
						dni.uom,
						p.total_weight AS weight,
						si.amount,
						si.net_amount,
						dn.name AS delivery_note,
						dn.posting_date AS delivery_date,
						t.name AS tx_row,
						t.charge_type,
						t.rate AS gst,
						t.tax_amount AS gst_amount,
						sle_out.valuation_rate AS cos
				FROM
					`tabDelivery Note` dn
				LEFT JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
				LEFT JOIN `tabSales Invoice Item` si ON si.dn_detail = dni.name
				LEFT JOIN `tabSales Invoice` s ON s.name = si.parent
				LEFT JOIN `tabSales Taxes and Charges` t ON t.parent = s.name
				LEFT JOIN `tabAddress` a ON a.name = COALESCE(dn.shipping_address_name, s.shipping_address_name)
				LEFT JOIN `tabPackaging` p ON p.name = COALESCE(si.uom, dni.uom)
				LEFT JOIN (SELECT 
					voucher_detail_no, item_code, batch_no, valuation_rate
				FROM
					`tabStock Ledger Entry`
				WHERE
					voucher_type = 'Delivery Note'
						AND actual_qty < 0
						AND is_cancelled = 0) sle_out ON sle_out.voucher_detail_no = dni.name
					AND sle_out.item_code = dni.item_code
					AND sle_out.batch_no = dni.batch_no
				WHERE
					dn.docstatus = 1
					and dn.is_replacement = 0 
					and dn.is_donation = 0
					{}
			UNION 
				SELECT 
					dd.document_date AS posting_date,
						dd.deleted_name AS sales_invoice,
						'Deleted' AS status,
						NULL AS customer,
						NULL AS total,
						NULL AS outlet_name,
						NULL AS item_code,
						NULL AS qty,
						NULL AS item_tax_rate,
						NULL AS rate,
						NULL AS uom,
						NULL AS weight,
						NULL AS amount,
						NULL AS net_amount,
						NULL AS delivery_note,
						NULL AS delivery_date,
						NULL AS tx_row,
						NULL AS charge_type,
						NULL AS gst,
						NULL AS gst_amount,
						NULL AS cos
				FROM
					`tabDeleted Document` dd
				WHERE
					dd.deleted_doctype = 'Sales Invoice' 
				{}) AS c
			where c.posting_date is not null
			{}
			ORDER BY c.posting_date DESC

		""".format(self.cond, self.cond_delete, self.cond_all), self.filters, as_dict=1, debug=0)
	
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