# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.utils import getdate, add_days
from erpnext.stock.doctype.batch.batch import get_batch_qty
from erpnext.stock.get_item_details import get_conversion_factor

class ScrapRequest(Document):
	def on_submit(self):
		name = create_material_issue(self)
		if name:
			self.db_set("stock_entry", name)

	def on_cancel(self):
		if self.stock_entry:
			doc = frappe.get_doc("Stock Entry", self.stock_entry)
			doc.cancel()

def create_material_issue(doc):
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type_view = "Scrap Materials"
	stock_entry.purpose = "Material Issue"
	stock_entry.set_stock_entry_type()
	# get warehouse and batch portion
	if doc.stock_entry:
		stock_entry = frappe.get_doc("Stock Entry", doc.stock_entry)
		if stock_entry.docstatus == 0:
			stock_entry.submit()
		return doc.stock_entry
	
	qty_all = 0
	for d in doc.get("items"):
		qty_map = get_batch_qty(d.batch)
		for dt in qty_map:
			row = stock_entry.append("items")
			row.item_code = d.item_code
			row.qty = dt.get("qty") or 1
			qty_all += row.qty
			row.uom = d.uom
			row.batch_no = d.batch
			row.is_scrap_item = 1
			row.request_no = doc.name
			row.conversion_factor = get_conversion_factor(d.item_code, d.uom).get("conversion_factor", 1)
			row.s_warehouse = dt.get("warehouse")

	if not qty_all:
		return 
	
	stock_entry.set_missing_values()
	stock_entry.insert(ignore_permissions=1)
	stock_entry.submit()

	return stock_entry.name



@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_warehouse(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.get_all("Warehouse", {"is_group":0},as_list=1)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_batch_numbers(doctype, txt, searchfield, start, page_len, filters):
	query = """select batch_id,  CONCAT("qty: ", round(batch_qty, 2)),  CONCAT("exp: ", expiry_date) from `tabBatch`
			where disabled = 0
			and name like {txt} """.format(
		txt=frappe.db.escape("%{0}%".format(txt))
	)

	if filters and filters.get("item"):
		query += " and item = {item}".format(item=frappe.db.escape(filters.get("item")))

	query += " order by expiry_date asc"
	return frappe.db.sql(query, filters)

def collect_expired_items():
	enable, within_days = frappe.db.get_value("Stock Settings","Stock Settings", ['enable_auto_collect_expired_items', 'expiry_days']) or 0, 0

	if not enable:
		return
	
	use_date = add_days(getdate(), within_days)

	# get data
	data = frappe.db.get_all("Batch", {"expiry_date": ['<', use_date], "batch_qty":['>', 0]}, ['name', 'item', 'batch_qty'])
	if not data:
		return

	# create scrap request
	doc = frappe.new_doc("Scrap Request")
	for d in data:
		row = doc.append("items")
		row.item_code = d.item
		row.batch = d.batch
		row.qty = d.batch_qty
		# warehouse
	doc.reason = "Expired item"
	doc.insert(ignore_permissions=1)
	return doc.name
