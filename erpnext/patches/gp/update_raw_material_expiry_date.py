import frappe
from frappe.utils import add_years


def execute():
	update_raw_material_expiry_dates()


def update_raw_material_expiry_dates():
	batches = frappe.db.sql(
		"""
		SELECT b.name, b.manufacturing_date
		FROM `tabBatch` b
		INNER JOIN `tabItem` i ON i.name = b.item
		WHERE i.item_group = 'Raw Material'
			AND b.manufacturing_date IS NOT NULL
			AND (b.expiry_date IS NULL OR b.expiry_date = '')
		""",
		as_dict=True,
	)

	for batch in batches:
		frappe.db.set_value(
			"Batch",
			batch.name,
			"expiry_date",
			add_years(batch.manufacturing_date, 3),
			update_modified=False,
		)

	frappe.db.commit()
	print(f"Updated expiry dates for {len(batches)} raw material batch(es).")
