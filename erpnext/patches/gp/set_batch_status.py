import frappe


def execute():
	set_batch_status()


def set_batch_status():
	"""Backfill Batch.status for existing records based on batch_qty and expiry_date.

	Rule (mirrors erpnext.stock.doctype.batch.batch.get_batch_status):
	- Expired: expiry_date is set and in the past
	- Empty: batch_qty <= 0
	- Active: otherwise
	"""
	print("Setting status on existing Batch records...")

	batch = frappe.qb.DocType("Batch")

	expired = (
		frappe.qb.update(batch)
		.set(batch.status, "Expired")
		.where(batch.expiry_date.isnotnull() & (batch.expiry_date < frappe.utils.getdate()))
		.run()
	)

	empty = (
		frappe.qb.update(batch)
		.set(batch.status, "Empty")
		.where(
			batch.batch_qty <= 0
		)
		.run()
	)

	active = (
		frappe.qb.update(batch)
		.set(batch.status, "Active")
		.where(
			(batch.batch_qty > 0)
			& (batch.expiry_date > frappe.utils.getdate())
		)
		.run()
	)

	frappe.db.commit()
	print("Batch status backfill done.")
