# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cstr
from erpnext.accounts.utils import  get_account_number_map
class CostCenterSettings(Document):
	def validate(self):
		for d in self.get("cost_center"):
			d.company = self.company

	@frappe.whitelist()
	def load_items(self):
		parent_company = frappe.get_value("Company", self.company, "parent_company")
		parent_company_cc = frappe.get_value("Company", parent_company, "cost_center")
		company_cc = frappe.get_value("Company", self.company, "cost_center")
		items = frappe.db.sql("""
			SELECT
				cc.account,
				cc.account_code,
				cc.cost_center
			FROM `tabCost Center Mapping` cc
			WHERE cc.parent = %s order by cc.idx asc;
		""", (parent_company), as_dict=1)

		account_map = get_account_number_map(self.company)

		for d in list(self.cost_center):
			self.remove(d)

		self.cost_center = []
		for d in items:
			row = self.append("cost_center")
			if d.cost_center == parent_company_cc:
				row.cost_center = company_cc

			row.account = account_map.get(d.account_code)
			row.account_code = d.account_code
			row.company = self.company