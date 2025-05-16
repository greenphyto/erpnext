# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.utils import getdate, add_days
from erpnext.stock.doctype.batch.batch import get_batch_qty
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.controllers.foms import get_wip_warehouse

class ScrapRequest(Document):
	def validate(self):
		if self.docstatus == 0:
			self.stock_entry = ""

		self.set_scrap_account()
		 
	def set_scrap_account(self):
		rm_account = frappe.db.get_single_value("Stock Settings", "account_for_raw_material_scrap")
		pr_account = frappe.db.get_single_value("Stock Settings", "account_for_product_scrap")
		for d in self.items:
			if d.item_group == "Raw Material":
				d.expense_account = rm_account
			if d.item_group == "Products":
				d.expense_account = pr_account		
			
	def on_submit(self):
		name = create_material_issue(self)
		if name:
			self.db_set("stock_entry", name)

	def on_cancel(self):
		if self.stock_entry:
			doc = frappe.get_doc("Stock Entry", self.stock_entry)
			doc.cancel()

def create_material_issue(doc, submit=False):
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type_view = "Scrap Materials"
	stock_entry.purpose = "Material Issue"
	stock_entry.remarks = "Expired items (system)"
	stock_entry.system_generated = doc.system_generated
	stock_entry.set_stock_entry_type()
	stock_entry.request_no = doc.name

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
			row.conversion_factor = get_conversion_factor(d.item_code, d.uom).get("conversion_factor", 1)
			row.s_warehouse = dt.get("warehouse")

	if not qty_all:
		return 
	
	stock_entry.set_missing_values()
	stock_entry.insert(ignore_permissions=1)
	if submit:
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
	wip_warehouse = get_wip_warehouse()

	# get data
	# only get expired batch on batch qty non WIP warehouse
	data = frappe.db.sql("""
		SELECT 
			*
		FROM
			(SELECT 
				sle.batch_no AS batch, b.item,
					sle.warehouse,
					SUM(sle.actual_qty) AS batch_qty,
					b.expiry_date
			FROM
				`tabStock Ledger Entry` sle
			LEFT JOIN `tabBatch` b ON b.name = sle.batch_no
			WHERE
				sle.is_cancelled = 0
					AND sle.batch_no IS NOT NULL
					AND sle.batch_no != ''
					AND sle.warehouse NOT IN %(wh)s
					AND b.expiry_date <= %(exp)s
					AND b.item_group = 'Raw Material'
			GROUP BY sle.batch_no , sle.warehouse
			ORDER BY sle.modified ASC) a
		WHERE
			a.batch_qty > 0
	""", {"wh":wip_warehouse, "exp":use_date}, as_dict=1)

	if not data:
		return
	
	sr_name = frappe.get_value("Scrap Request", {
		"system_generated":1, 
		"docstatus":0
	}, debug=0)

	if sr_name:
		doc = frappe.get_doc("Scrap Request", sr_name)
		# add tollerance approval on progress not more than 14 days ago
		if doc.workflow_state != "Pending" and getdate(doc.posting_date) > add_days(getdate(), -14):
			return
	else:
		doc = frappe.new_doc("Scrap Request")

	# create scrap request
	for d in data:
		temp = doc.get("items", {"batch":d.batch})
		if temp:
			row = temp[0]
		else:
			row = doc.append("items")
			row.item_code = d.item
			row.batch = d.batch

		row.qty = d.batch_qty

	doc.posting_date = getdate()
	doc.reason = "Expired item (system)"
	doc.system_generated = 1
	doc.save(ignore_permissions=1)
	return doc.name

def collect_expired_product(date=""):
	enable = frappe.db.get_value("Stock Settings","Stock Settings", 'enable_auto_collect_expired_products') or 0

	if not enable:
		return
	
	use_date = getdate(date)
	wip_warehouse = get_wip_warehouse()

	# get data
	# only get expired batch on batch qty non WIP warehouse
	data = frappe.db.sql("""
		SELECT 
			*
		FROM
			(SELECT 
				sle.batch_no AS batch, b.item,
					sle.warehouse,
					SUM(sle.actual_qty) AS batch_qty,
					b.expiry_date,
					sle.stock_uom as uom
			FROM
				`tabStock Ledger Entry` sle
			LEFT JOIN `tabBatch` b ON b.name = sle.batch_no
			WHERE
				sle.is_cancelled = 0
					AND sle.batch_no IS NOT NULL
					AND sle.batch_no != ''
					AND sle.warehouse NOT IN %(wh)s
					AND b.expiry_date <= %(exp)s
					AND b.item_group = 'Products'
			GROUP BY sle.batch_no , sle.warehouse
			ORDER BY sle.modified ASC) a
		WHERE
			a.batch_qty > 0
	""", {"wh":wip_warehouse, "exp":use_date}, as_dict=1)

	if not data:
		return

	# create SE directly
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type_view = "Waste Materials"
	stock_entry.purpose = "Material Issue"
	stock_entry.set_stock_entry_type()
	stock_entry.request_no = "Expired Product"
	expense_account = frappe.db.get_single_value("Stock Settings", "account_for_product_scrap")

	for d in data:
		row = stock_entry.append("items")
		row.item_code = d.item
		row.qty = d.batch_qty
		row.uom = d.uom
		row.batch_no = d.batch
		row.is_scrap_item = 1
		row.conversion_factor = 1
		row.s_warehouse = d.get("warehouse")
		row.expense_account = expense_account
	
	stock_entry.system_generated = 1
	stock_entry.remarks = "Expired products (system)"
	stock_entry.set_missing_values()
	stock_entry.insert(ignore_permissions=1)
	stock_entry.submit()

	return stock_entry.name
