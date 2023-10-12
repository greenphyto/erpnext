# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import cint


class BuyingSettings(Document):
	def validate(self):
		for key in ["supplier_group", "supp_master_name", "maintain_same_rate", "buying_price_list"]:
			frappe.db.set_default(key, self.get(key, ""))

		from erpnext.utilities.naming import set_by_naming_series

		set_by_naming_series(
			"Supplier",
			"supplier_name",
			self.get("supp_master_name") == "Naming Series",
			hide_name_field=False,
		)


	@frappe.whitelist()
	def update_supplier_account(self):
		for d in self.get("default_supplier_account"):
			series = d.code.replace("...", "")
			suppliers = frappe.db.get_all("Supplier", {"supplier_code":["like", series+"%"]})
			for sup in suppliers:
				doc = frappe.get_doc("Supplier", sup.name)
				change = False
				for row in doc.get("accounts"):
					if row.company == d.company:
						row.account = d.account
						change = True
				
				if not change:
					row = doc.append("accounts")
					row.account = d.account
					row.company = d.company

				doc.save()

def get_series_pr_required(series):
	res = frappe.get_value("Series PO required PR", {
		"series": series,
		"parent":"Buying Settings",
		"parentfield":"series_required_pr",
	}, "require_pr")

	return cint(res)