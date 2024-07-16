# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Key(Document):
	pass


@frappe.whitelist()
def get_key():
	return frappe.db.sql("select name as value, concat(name,' (',room,')') as label from `tabKey`", as_dict=True)