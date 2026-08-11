import frappe


def execute():
	set_rnd_product()


def set_rnd_product():
	item = frappe.qb.DocType("Item")

	frappe.qb.update(item).set(item.rnd_product, 1).where(
		item.item_name.like("%R&D%")
	).run()

	items = frappe.get_all("Item", filters={"rnd_product": 1}, fields=["name"])
	for row in items:
		defaults = frappe.get_all("Item Default", filters={"parent": row.name}, fields=["name", "company"])
		for d in defaults:
			company = frappe.get_cached_doc("Company", d.company)
			updates = {}
			if company.get("default_rnd_expense"):
				updates["expense_account"] = company.default_rnd_expense
			if company.get("default_rnd_cost_center"):
				updates["selling_cost_center"] = company.default_rnd_cost_center
			if updates:
				frappe.db.set_value("Item Default", d.name, updates)

	frappe.db.commit()
