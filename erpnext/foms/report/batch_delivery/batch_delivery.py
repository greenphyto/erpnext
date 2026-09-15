# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

"""
Report for daily accumulation broker vs stock
"""

import frappe
from frappe.utils import flt
from frappe.query_builder.functions import CombineDatetime
from pypika import Order

def execute(filters=None):
	return Report(filters).execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_condition(self):
		self.cond = ""
		if self.filters.get("item_code"):
			self.cond += (" and i.item_code = %(item_code)s ")
		if self.filters.get("customer"):
			self.cond += (" and d.customer = %(customer)s ")
		if self.filters.get("batch_no"):
			self.cond += (" and i.batch_no = %(batch_no)s ")

	def setup_column(self):
		self.columns = [
			{"fieldname": "batch_no", 		"label": "Batch No", 	"fieldtype": "Link", "width":160, "options":"Batch"},
			{"fieldname": "wo_id", 			"label": "Work Order ID","fieldtype": "Link", "width":120, "options":"Work Order"},
			{"fieldname": "lot_id", 		"label": "FOMS Lot ID",	"fieldtype": "Data", "width":110, "options":""},
			{"fieldname": "item_code", 		"label": "Item", 		"fieldtype": "Data", "width":200, "options":""},
			{"fieldname": "expiry_date", 	"label": "Exp. Date", 	"fieldtype": "Date", "width":100, "options":""},
			{"fieldname": "prod_qty_kg", 	"label": "Qty KG", 		"fieldtype": "Float", "width":80, "options":""},
			{"fieldname": "prod_qty", 		"label": "Qty Pack", 	"fieldtype": "Float", "width":80, "options":""},
			{"fieldname": "delivery_note",	"label": "DO No", 		"fieldtype": "Link", "width":150, "options":"Delivery Note"},
			{"fieldname": "delivery_date", 	"label": "Deliv. Date", "fieldtype": "Date", "width":120, "options":""},
			{"fieldname": "scrap_material", "label": "Scrap Material", "fieldtype": "Link", "width":150, "options":"Stock Entry"},
			{"fieldname": "dis_date",		"label": "Disposal Date",  "fieldtype": "Date", "width":120, "options":""},
			{"fieldname": "qty", 			"label": "Qty Sent", 	"fieldtype": "Float", "width":80, "options":""},
			{"fieldname": "uom_pack", 		"label": "UOM", 		"fieldtype": "Data", "width":130, "options":""},
			{"fieldname": "customer", 		"label": "Customer", 	"fieldtype": "Link", "width":220, "options":"Customer"},
			{"fieldname": "address_title", 	"label": "Outlets", 	"fieldtype": "", "width":400, "options":""},
		]
		

	def get_qty_prod_map(self):
		self.qty_map = frappe._dict({})
		data = frappe.db.sql("""
				SELECT 
					l.batch_no,
					l.name,
					l.voucher_no,
					wo.name AS wo_id,
					wo.foms_lot_name AS lot_id,
					SUM(l.actual_qty) / u.conversion_factor AS qty,
					SUM(l.actual_qty) AS qty_kg,
					l.item_code,
					l.voucher_type,
					wo.packet_size,
					wo.conversion_factor
				FROM
					`tabStock Ledger Entry` l
						LEFT JOIN
					`tabStock Entry` se ON se.name = l.voucher_no
						LEFT JOIN
					`tabWork Order` wo ON wo.name = se.work_order
						LEFT JOIN
					tabItem i ON i.name = l.item_code
					   	LEFT JOIN
					`tabUOM Conversion Detail` u ON u.uom = i.default_packaging
							AND u.parent = i.name
				WHERE
					l.is_cancelled = 0
						and (l.voucher_type = "Stock Reconciliation" or (l.voucher_type = "Stock Entry" AND se.purpose IN ('Manufacture', 'Material Receipt')))
						AND i.is_stock_item = 1
						AND i.item_group = 'Products'
				GROUP BY l.batch_no
				""", as_dict=1)

		for d in data:
			self.qty_map[d.batch_no] = d

	def get_data(self):
		# get manufature
		# get delivery
		# get scrap
		self.get_qty_prod_map()
		self.raw_data = self.get_stock_ledger_entries()

	def get_stock_ledger_entries(self):
		filters = self.filters
		sle = frappe.qb.DocType("Stock Ledger Entry")
		dn_doc = frappe.qb.DocType("Delivery Note")
		item_db = frappe.qb.DocType("Item")
		addr_db = frappe.qb.DocType("Address")
		uom_db = frappe.qb.DocType("UOM Conversion Detail")
		query = (
			frappe.qb.from_(sle)
			.select(
				sle.item_code,
				CombineDatetime(sle.posting_date, sle.posting_time).as_("date"),
				sle.warehouse,
				sle.posting_date,
				sle.posting_time,
				sle.actual_qty,
				sle.incoming_rate,
				sle.valuation_rate,
				sle.company,
				sle.voucher_type,
				sle.qty_after_transaction,
				sle.stock_value_difference,
				sle.voucher_no,
				sle.stock_value,
				sle.batch_no,
				sle.serial_no,
				sle.project,
				dn_doc.customer,
				dn_doc.posting_date.as_("delivery_date"),
				item_db.default_packaging.as_("uom_pack"),
				uom_db.conversion_factor.as_("conv_factor"),
				addr_db.address_title.as_("address_title"),
			)
			.left_join(dn_doc).on(sle.voucher_no == dn_doc.name)
			.left_join(item_db).on(sle.item_code == item_db.name)
			.left_join(addr_db).on(addr_db.name == dn_doc.shipping_address_name)
			.left_join(uom_db).on((uom_db.parent == sle.item_code) & (uom_db.uom == item_db.default_packaging))
			.where(
				(sle.docstatus < 2)
				& (sle.is_cancelled == 0)
				& (item_db.item_group == "Products")
			)
			.orderby(sle.batch_no, order=Order.desc)
			.orderby(CombineDatetime(sle.posting_date, sle.posting_time))
			.orderby(sle.creation)
		)

		for field in ["batch_no", "item_code"]:
			if filters.get(field):
				query = query.where(sle[field] == filters.get(field))

		return query.run(as_dict=True, debug=0)
	
	def process_data(self):
		self.data = []
		now_batch = ""
		total_qty_sent = 0
		total_qty_sent_kg = 0
		pack_uom = ""
		pack_conv = 1

		for d in self.raw_data:
			if not now_batch or now_batch != d.batch_no:
				# last from previous
				if now_batch:
					self.data.append({"item_code":"Qty Left", "prod_qty":flt(temp.get("qty"))-total_qty_sent, "prod_qty_kg":flt(temp.get("qty_kg"))-total_qty_sent_kg, "qty":total_qty_sent})
					total_qty_sent = 0
					total_qty_sent_kg = 0
				
				# comers
				now_batch = d.batch_no
				temp = self.qty_map.get(d.batch_no) or {}
				d.prod_qty = flt(temp.get("qty"))
				d.prod_qty_kg = flt(temp.get("qty_kg"))
				d.wo_id = temp.get("wo_id")
				d.lot_id = temp.get("lot_id")
				if d.voucher_type == "Delivery Note":
					d.delivery_note = d.voucher_no
					d.qty = d.actual_qty *-1

				self.data.append(d)
			
			if d.voucher_type == "Delivery Note":
				d.delivery_note = d.voucher_no
				d.qty = d.actual_qty *-1 / d.conv_factor
				d.stock_qty = d.actual_qty *-1

				total_qty_sent += flt(d.qty)
				total_qty_sent_kg += flt(d.stock_qty)
				d.batch_no = ""
				d.item_code = ""
				d.expiry_date = ""
				self.data.append(d)
			
			if d.voucher_type == "Stock Entry" and "SM" in d.voucher_no:
				d.qty = d.actual_qty *-1 / d.conv_factor
				d.stock_qty = d.actual_qty *-1 
				d.scrap_material = d.voucher_no
				d.dis_date = d.posting_date

				total_qty_sent += flt(d.qty)
				total_qty_sent_kg += flt(d.stock_qty)
				d.batch_no = ""
				d.item_code = ""
				d.expiry_date = ""
				self.data.append(d)

		if self.raw_data:
			self.data.append({"item_code":"Qty Left", "prod_qty":flt(temp.get("qty"))-total_qty_sent, "prod_qty_kg":flt(temp.get("qty_kg"))-total_qty_sent_kg, "qty":total_qty_sent})
	
	
	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data