import frappe


def execute():
	"""Add composite index on GL Entry to speed up General Ledger report.

	The report filters with `(posting_date >= from_date OR is_opening = 'Yes')`.
	Without an index covering is_opening, MariaDB does a full table scan on
	every run regardless of date range (even today-today), because the OR
	clause defeats the single-column posting_date/company indexes.

	This composite index lets the optimizer resolve both the period range
	and the opening lookup via index, removing the full scan.
	"""
	add_gl_entry_opening_index()


def add_gl_entry_opening_index():
	index_name = "company_is_opening_posting_date_index"

	existing = frappe.db.sql(
		"""SHOW INDEX FROM `tabGL Entry` WHERE Key_name = %s""",
		index_name,
	)
	if existing:
		print(f"Index {index_name} already exists on tabGL Entry, skipping.")
		return

	legacy = frappe.db.sql(
		"""SHOW INDEX FROM `tabGL Entry` WHERE Key_name = 'idx_tmp_company_opening'"""
	)
	if legacy:
		frappe.db.sql("ALTER TABLE `tabGL Entry` DROP INDEX idx_tmp_company_opening")
		print("Dropped temporary index idx_tmp_company_opening.")

	frappe.db.add_index(
		"GL Entry",
		["company", "is_opening", "posting_date"],
		index_name=index_name,
	)
	print(f"Added index {index_name} on tabGL Entry.")
