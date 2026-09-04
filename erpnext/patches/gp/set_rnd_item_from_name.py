import frappe

# bench --site test6 execute erpnext.patches.gp.set_rnd_item_from_name.execute
def execute():
	frappe.db.sql(
		"""
		UPDATE `tabItem`
		SET rnd_item = 1
		WHERE item_name LIKE %(pattern)s
		""",
		{"pattern": "(R&D)%"},
	)

	for company in frappe.get_all("Company", fields=["name", "abbr"]):
		account = f"622001 - R&D Consumable - {company.abbr}"
		if frappe.db.exists("Account", {"name": account, "company": company.name}):
			frappe.db.set_value("Company", company.name, "account_for_rnd_item_scrap", account)
