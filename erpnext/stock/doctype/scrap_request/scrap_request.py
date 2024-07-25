# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.utils import getdate, add_days

class ScrapRequest(Document):
	pass


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
