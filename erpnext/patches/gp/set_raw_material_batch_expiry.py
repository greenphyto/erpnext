import frappe


def execute():
	batch = frappe.qb.DocType("Batch")

	frappe.qb.update(batch).set(
		batch.expiry_date, "2099-01-01"
	).where(
		batch.item_group == "Raw Material"
	).run()

	frappe.db.commit()
