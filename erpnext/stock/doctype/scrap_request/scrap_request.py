# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.utils import getdate, add_days, cint
from erpnext.stock.doctype.batch.batch import get_batch_qty
from erpnext.stock.get_item_details import get_conversion_factor
# from erpnext.controllers.foms import get_wip_warehouse
from erpnext.gp_erp.controllers.setup.company import switch_to_company_admin
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
		name = create_material_issue(self, True)
		if name:
			self.db_set("stock_entry", name)

	def on_cancel(self):
		if self.stock_entry:
			doc = frappe.get_doc("Stock Entry", self.stock_entry)
			if doc.docstatus == 1:
				doc.cancel()
			elif doc.docstatus == 0:
				frappe.delete_doc("Stock Entry", doc.stock_entry)
				doc.db_set("stock_entry", "")

@frappe.whitelist()
def get_scrap_account(item_group):
	account = ""
	if item_group == "Raw Material":
		account = frappe.db.get_single_value("Stock Settings", "account_for_raw_material_scrap")
	elif item_group == "Products":
		account = frappe.db.get_single_value("Stock Settings", "account_for_product_scrap")
	return account

def create_material_issue(doc, submit=False):
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type_view = "Scrap Materials"
	stock_entry.purpose = "Material Issue"
	stock_entry.remarks = "Expired items (system)"
	stock_entry.system_generated = doc.system_generated
	stock_entry.set_stock_entry_type()
	stock_entry.request_no = doc.name
	stock_entry.posting_date = doc.posting_date
	stock_entry.set_posting_time = 1


	# get warehouse and batch portion
	if doc.stock_entry:
		stock_entry = frappe.get_doc("Stock Entry", doc.stock_entry)
		if stock_entry.docstatus == 0:
			stock_entry.submit()
		return doc.stock_entry
	
	qty_all = 0
	wip_warehouse = get_wip_warehouse()
	for d in doc.get("items"):
		qty_map = get_batch_qty(d.batch)
		for dt in qty_map:
			if dt.get("warehouse") not in wip_warehouse:
				row = stock_entry.append("items")
				row.item_code = d.item_code
				row.qty = dt.get("qty") or 1
				qty_all += row.qty
				row.uom = d.uom
				row.batch_no = d.batch
				row.is_scrap_item = 1
				row.conversion_factor = get_conversion_factor(d.item_code, d.uom).get("conversion_factor", 1)
				row.s_warehouse = dt.get("warehouse")
				row.expense_account = d.expense_account

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
	enable, within_days = frappe.db.get_value("Stock Settings","Stock Settings", ['enable_auto_collect_expired_items', 'expiry_days']) or (0, 0)

	if not cint(enable):
		return
	
	use_date = add_days(getdate(), cint(within_days))
	wip_warehouse = get_wip_warehouse()

	# get data
	# only get expired batch on batch qty non WIP warehouse
	data = frappe.db.sql("""
		SELECT 
			*
		FROM
			(SELECT 
				sle.batch_no AS batch,
					b.item,
					sle.warehouse,
					sle.company,
					SUM(sle.actual_qty) AS batch_qty,
					b.expiry_date
			FROM
				`tabStock Ledger Entry` sle
			LEFT JOIN `tabBatch` b ON b.name = sle.batch_no
			left join `tabItem` i on i.name = sle.item_code
			WHERE
				sle.is_cancelled = 0
					AND sle.batch_no IS NOT NULL
					AND sle.batch_no != ''
					AND sle.warehouse NOT IN %(wh)s
					AND b.expiry_date <= %(exp)s
					AND i.item_group = 'Raw Material'
			GROUP BY sle.batch_no , sle.warehouse
			ORDER BY sle.modified ASC) a
		WHERE
			a.batch_qty > 0
	""", {"wh":wip_warehouse, "exp":use_date}, as_dict=1, debug=0)

	if not data:
		return

	companys = list(set([d.company for d in data]))
	result = {}
	
	for company in companys:
		switch_to_company_admin(company)
		sr_name = frappe.get_value("Scrap Request", {
			"system_generated":1, 
			"docstatus":0
		}, debug=0)

		if sr_name:
			doc = frappe.get_doc("Scrap Request", sr_name)
			# add tollerance approval on progress not more than 14 days ago
			if doc.status != "Pending" and getdate(doc.posting_date) > add_days(getdate(), -14):
				return
		else:
			doc = frappe.new_doc("Scrap Request")

		# create scrap request
		for d in data:
			if d.company != company:
				continue

			temp = doc.get("items", {"batch":d.batch})
			if temp:
				row = temp[0]
			else:
				row = doc.append("items")
				row.item_code = d.item
				row.batch = d.batch

			row.qty = d.batch_qty
		
		rm_account = frappe.db.get_value("Company", company, "account_for_raw_material_scrap")
		for d in doc.items:
			if d.item_group == "Raw Material":
				d.expense_account = rm_account	

		doc.posting_date = getdate()
		doc.scrap_account = rm_account
		doc.reason = "Expired item (system)"
		doc.system_generated = 1
		doc.save(ignore_permissions=1)
		result[company] = doc.name

	return result

def collect_expired_product(date=""):
	enable, within_days = frappe.db.get_value("Stock Settings","Stock Settings", ['enable_auto_collect_expired_products', 'expiry_days_product']) or (0,0)

	if not cint(enable):
		return
	
	use_date = add_days(getdate(date), cint(within_days))
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
					sle.company,
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
			ORDER BY sle.company, b.expiry_date ASC) a
		WHERE
			a.batch_qty > 0
	""", {"wh":wip_warehouse, "exp":use_date}, as_dict=1, debug=0)

	if not data:
		return
	companys = list(set([d.company for d in data]))
	result = {}
	for company in companys:
		switch_to_company_admin(company)

		# create SE directly
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.company = company
		stock_entry.stock_entry_type_view = "Waste Materials"
		stock_entry.purpose = "Material Issue"
		stock_entry.set_stock_entry_type()
		stock_entry.request_no = "Expired Product"
		expense_account = frappe.db.get_value("Company", company, "account_for_product_scrap")
		cost_center = frappe.db.get_value("Company", company, "cost_center")

		for d in data:
			if d.company != company:
				continue
			row = stock_entry.append("items")
			row.item_code = d.item
			row.qty = d.batch_qty
			row.uom = d.uom
			row.batch_no = d.batch
			row.is_scrap_item = 1
			row.conversion_factor = 1
			row.s_warehouse = d.get("warehouse")
			row.expense_account = expense_account
			row.cost_center = cost_center
		
		stock_entry.system_generated = 1
		stock_entry.remarks = "Expired products (system)"
		stock_entry.set_missing_values()
		stock_entry.insert(ignore_permissions=1)
		stock_entry.submit()
		# try:
		# except Exception as e:
		# 	frappe.log_error(frappe.get_traceback(), "Submit Stock Entry Failed for expired product")
		# gl_entries = frappe.db.get_list(
		# 	"GL Entry",
		# 	filters={
		# 		"voucher_type": "Stock Entry",
		# 		"voucher_no": stock_entry.name
		# 	},
		# 	fields=[
		# 		"name",
		# 		"posting_date",
		# 		"account",
		# 		"debit",
		# 		"credit",
		# 		"voucher_type",
		# 		"voucher_no",
		# 		"remarks",
		# 		"company",
		# 		"cost_center"
		# 	],
		# 	order_by="posting_date asc, creation asc"
		# )
		result[company] = stock_entry.name

	return result
