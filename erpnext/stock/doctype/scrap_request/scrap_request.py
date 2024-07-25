# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.desk.reportview import get_filters_cond, get_match_cond

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
