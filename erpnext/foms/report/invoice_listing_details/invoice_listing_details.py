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
		self.cond = " AND si.income_account = %(income_account)s "
		self.cond_delete = ""
		self.cond_dn = ""

		if self.filters.get("customer"):
			self.cond += " and s.customer = %(customer)s "
		if self.filters.get("sales_invoice"):
			self.cond += " and s.name = %(sales_invoice)s "

		today = datetime.date.today()
		first_day = today.replace(day=1)
		last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
		self.filters.start_date = self.filters.get("start_date") or first_day
		self.filters.end_date = self.filters.get("end_date") or last_day
		self.cond += " and s.posting_date between %(start_date)s and %(end_date)s "
		self.cond_dn += " and dn.posting_date between %(start_date)s and %(end_date)s "
		self.cond_delete += " and dd.document_date between %(start_date)s and %(end_date)s "

		if cint(self.filters.get("show_credit_note")):
			self.cond += " and s.is_return = 1 "

	def setup_column(self):
		self.columns = [
			{"fieldname": "posting_date", 	"label": "Invoice Date", "fieldtype": "Date", 	"width":120, "options":""},
			{"fieldname": "sales_invoice", 	"label": "Invoice No", 	"fieldtype": "Link", 	"width":120, "options":"Sales Invoice"},
			{"fieldname": "status", 		"label": "Status", 		"fieldtype": "Data", 	"width":80, "options":""},
			{"fieldname": "customer", 		"label": "Customer", 	"fieldtype": "Link", 	"width":220, "options":"Customer"},
			{"fieldname": "outlet_name", 	"label": "Store Name", 	"fieldtype": "Data", 	"width":220, "options":""},
			{"fieldname": "delivery_note", 	"label": "Delivery Note","fieldtype": "Link", 	"width":140, "options":"Delivery Note"},
			{"fieldname": "delivery_date", 	"label": "Delivery Date","fieldtype": "Date", 	"width":120, "options":""},
			{"fieldname": "item_code", 		"label": "Item", 		"fieldtype": "Link", 	"width":100, "options":"Item"},
			{"fieldname": "qty", 			"label": "Qty", 		"fieldtype": "Float", 	"width":80, "options":""},
			{"fieldname": "uom", 			"label": "UOM", 		"fieldtype": "Link", 	"width":180, "options":"UOM"},
			{"fieldname": "weight", 		"label": "Weight (KG)", "fieldtype": "Float", 	"width":100, "options":""},
			{"fieldname": "total_weight", 		"label": "Total Weight (KG)", "fieldtype": "Float", 	"width":140, "options":""},
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
				s.posting_date,
				s.name AS sales_invoice,
				s.customer,
				s.total,
				"Submitted" as status,
				a.outlet_name,
				si.item_code,
				si.qty,
				si.item_tax_rate,
				si.rate,
				si.uom,
				p.total_weight as weight,
				si.stock_qty as total_weight,
				si.amount,
				si.net_amount,
				dn.name as delivery_note,
				dn.posting_date as delivery_date,
				si.net_amount,
				t.name AS tx_row,
				t.charge_type,
				t.rate as gst,
				t.tax_amount as gst_amount,
				sle_out.valuation_rate AS cos
			FROM
				`tabSales Invoice` s
					LEFT JOIN
				`tabSales Invoice Item` si ON si.parent = s.name 
					LEFT JOIN
				`tabSales Taxes and Charges` t ON t.parent = s.name
					left join
				`tabAddress` a on a.name = s.shipping_address_name
					LEFT JOIN
				`tabPackaging` p ON p.name = si.uom
					LEFT JOIN
				`tabDelivery Note Item` dni ON dni.name = si.dn_detail
					LEFT JOIN
				`tabDelivery Note` dn ON dn.name = dni.parent
					LEFT JOIN
				(SELECT 
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
				s.docstatus = 1
				{}
			ORDER BY s.posting_date desc
		""".format(self.cond), self.filters, as_dict=1)

		self.raw_data_single = frappe.db.sql("""
			SELECT 
				dn.customer,
				dni.item_code,
				dni.qty,
				dni.uom,
				dni.rate,
				dni.amount,
				p.total_weight as weight,
				a.outlet_name,
				dn.name AS delivery_note,
				dni.stock_qty as total_weight,
				dn.posting_date AS delivery_date,
				sle_out.valuation_rate AS cos
			FROM
				`tabDelivery Note` dn
					LEFT JOIN
				`tabDelivery Note Item` dni ON dni.parent = dn.name
					LEFT JOIN
				`tabPackaging` p ON p.name = dni.uom
					LEFT JOIN
				`tabAddress` a on a.name = dn.shipping_address_name
					LEFT JOIN
				(SELECT 
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
					AND dn.is_replacement = 0
					AND dn.is_donation = 0
					AND dni.si_detail is null
					{}  
			ORDER BY dn.posting_date desc
		""".format(self.cond_dn), self.filters, as_dict=1, debug=0)

		self.raw_data_deleted = frappe.db.sql("""
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
				{}
			ORDER BY dd.document_date DESC			
		""".format(self.cond_delete), self.filters, as_dict=1)
	
	def process_data(self):
		self.data = []

		total_row = {
			"sales_invoice":"TOTAL",
			"amount":0,
			"gst_amount":0,
			"total_weight":0,
			"gst_amount":0,
			"total_amount":0
		}
		if not self.filters.get("show_missing_invoice"):
			for d in self.raw_data:
				# calculate tax amount
				if d.total:
					d.gst_amount = flt(d.amount)/flt(d.total)*flt(d.gst_amount)
					d.total_amount = d.gst_amount + flt(d.amount)
				
				total_row["gst_amount"] += d.gst_amount
				total_row["total_weight"] += d.total_weight
				total_row["total_amount"] += d.total_amount
				total_row["amount"] += d.amount

				self.data.append(d)
			if self.raw_data:
				self.data.append(total_row)

		total_row_single = {
			"sales_invoice":"TOTAL",
			"amount":0,
			"total_weight":0,
			"gst_amount":0,
			"total_amount":0
		}
		if self.raw_data_single:
			self.data.append({})
			for d in self.raw_data_single:
				self.data.append(d)
				total_row_single["total_weight"] += d.total_weight
				total_row_single["amount"] += d.amount

			if self.raw_data_single:
				self.data.append(total_row_single)

		if not self.filters.get("show_missing_invoice"):
			if self.raw_data_deleted:
				self.data.append({})
				self.data += self.raw_data_deleted

	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data