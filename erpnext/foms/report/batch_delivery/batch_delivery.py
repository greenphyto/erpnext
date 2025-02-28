# Copyright (c) 2013, erfidner.id and contributors
# For license information, please see license.txt

"""
Report for daily accumulation broker vs stock
"""

import frappe
from frappe.utils import flt

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
			{"fieldname": "delivery_date", 	"label": "Deliv. Date", "fieldtype": "Date", "width":100, "options":""},
			{"fieldname": "qty", 			"label": "Qty Sent", 	"fieldtype": "Float", "width":80, "options":""},
			{"fieldname": "uom", 			"label": "UOM", 		"fieldtype": "Data", "width":130, "options":""},
			{"fieldname": "customer", 		"label": "Customer", 	"fieldtype": "Link", "width":220, "options":"Customer"},
		]
	
	def get_data(self):
		self.raw_data = frappe.db.sql("""
			SELECT 
				b.name AS batch_no,
				b.item_name AS item_code,
				b.expiry_date,
				d.name AS delivery_note,
				d.delivery_completed_at AS delivery_date,
				d.customer,
				i.uom,
				i.qty,
				i.stock_qty
			FROM
				tabBatch AS b
					LEFT JOIN
				`tabItem` it ON it.name = b.item
					LEFT JOIN
				`tabDelivery Note Item` i ON i.batch_no = b.name
					INNER JOIN
				`tabDelivery Note` d ON d.name = i.parent AND d.docstatus = 1

			WHERE
				b.docstatus = 0
				AND it.item_group = 'Products' 
				{}
			ORDER BY b.expiry_date DESC , i.batch_no
		""".format(self.cond), self.filters, as_dict=1, debug=0)
		self.get_qty_prod_map()
		self.get_scrap_data()

	def get_scrap_data(self):
		self.qty_scrap = {}
		temp = frappe.db.sql("""
			SELECT 
				b.name AS batch_no,
				b.item_name AS item_code,
				b.expiry_date,
				d.name AS stock_entry,
				d.posting_date AS delivery_date,
				i.uom,
				i.qty,
				u.conversion_factor,
				i.qty / u.conversion_factor AS qty_pack,
				u.uom
			FROM
				tabBatch AS b
					LEFT JOIN
				`tabItem` it ON it.name = b.item
					LEFT JOIN
				`tabStock Entry Detail` i ON i.batch_no = b.name
					INNER JOIN
				`tabStock Entry` d ON d.name = i.parent AND d.docstatus = 1
					LEFT JOIN
				`tabUOM Conversion Detail` u ON u.parent = it.name
					AND u.uom = it.default_packaging
			WHERE
				b.docstatus = 0
					AND it.item_group = 'Products'
					AND i.t_warehouse IS NULL
		""", as_dict=1)

		for d in temp:
			self.qty_scrap[d.batch_no] = d
		

	def get_qty_prod_map(self):
		self.qty_map = frappe._dict({})
		data = frappe.db.sql("""
			SELECT 
				l.batch_no,
				l.name,
				l.voucher_no,
				wo.name as wo_id,
				wo.foms_lot_name as lot_id,
				SUM(l.actual_qty / wo.conversion_factor) AS qty,
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
			WHERE
				l.is_cancelled = 0 AND l.actual_qty > 0
					AND i.is_stock_item = 1
					AND i.item_group = 'Products'
			GROUP BY l.batch_no
				""", as_dict=1)

		for d in data:
			self.qty_map[d.batch_no] = d
	
	def process_data(self):
		self.data = []
		added = []
		now_batch = ""
		total_qty_sent = 0
		total_qty_sent_kg = 0

		for d in self.raw_data:
			if d.batch_no in added:
				now_batch = d.batch_no
				d.batch_no = ""
				d.item_code = ""
				d.expiry_date = ""
				self.data.append(d)
				total_qty_sent += flt(d.qty)
				total_qty_sent_kg += flt(d.stock_qty)
				continue

			if now_batch:
				# scrap issue
				scrap_data = self.qty_scrap.get(d.batch_no)
				if scrap_data:
					self.data.append({
						"delivery_note":scrap_data.stock_entry,
						"delivery_date":scrap_data.delivery_date,
						"qty":scrap_data.qty_pack,
						"uom":scrap_data.uom
					})
					total_qty_sent += flt(scrap_data.qty_pack)
					total_qty_sent_kg += flt(scrap_data.qty)
				self.data.append({"item_code":"Qty Left", "prod_qty":flt(temp.get("qty"))-total_qty_sent, "prod_qty_kg":flt(temp.get("qty_kg"))-total_qty_sent_kg, "qty":total_qty_sent})
				total_qty_sent = 0
				total_qty_sent_kg = 0

			total_qty_sent += flt(d.qty)
			total_qty_sent_kg += flt(d.stock_qty)

			temp = self.qty_map.get(d.batch_no) or {}
			d.prod_qty = flt(temp.get("qty"))
			d.prod_qty_kg = flt(temp.get("qty_kg"))
			d.delivery_note = d.delivery_note or temp.voucher_type
			d.wo_id = temp.get("wo_id")
			d.lot_id = temp.get("lot_id")
			added.append(d.batch_no)
			self.data.append(d)

		if self.raw_data:
			scrap_data = self.qty_scrap.get(now_batch)
			if scrap_data:
				self.data.append({
					"delivery_note":scrap_data.stock_entry,
					"delivery_date":scrap_data.delivery_date,
					"qty":scrap_data.qty_pack,
					"uom":scrap_data.uom
				})
				total_qty_sent += flt(scrap_data.qty_pack)
				total_qty_sent_kg += flt(scrap_data.qty)
			self.data.append({"item_code":"Qty Left", "prod_qty":flt(temp.get("qty"))-total_qty_sent, "prod_qty_kg":flt(temp.get("qty_kg"))-total_qty_sent_kg, "qty":total_qty_sent})


		
	def execute(self):
		self.setup_condition()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data