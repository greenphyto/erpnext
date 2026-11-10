import frappe
from frappe.utils import add_days, flt, today

from erpnext.controllers.foms import get_wip_warehouse
from erpnext.setup.doctype.company.company import switch_to_company_admin
from erpnext.stock.get_item_details import get_conversion_factor

# Batches with an inventory value below this threshold are written off
# automatically, without R&D validation, as testing them costs more than
# their immaterial value.
AUTO_WRITE_OFF_THRESHOLD = 100.0

# Stock Entry Type used for the automatic write-off.
WRITE_OFF_STOCK_ENTRY_TYPE = "Scrap Materials"


def get_context(context):
	pass


def get_aged_raw_material_batches():
	"""Return aged Raw Material batches, each annotated with its stock value.

	The age reference is the last audit date when the batch has been audited,
	otherwise the manufacturing date. A batch is considered aged when that
	reference date is older than one year.
	"""
	one_year_ago = add_days(today(), -365)

	batches = frappe.get_all(
		"Batch",
		filters={
			"item_group": "Raw Material",
			"batch_qty": [">", 0],
			"disabled": 0,
			# batch with expiry_date is considered already curated by user, skip it
			"expiry_date": ["is", "not set"],
			# aged if COALESCE(last_audited, manufacturing_date) <= one_year_ago
			"ifnull(last_audited, manufacturing_date)": ["<=", one_year_ago],
		},
		fields=[
			"name", "item", "item_name", "item_group", "manufacturing_date",
			"last_audited", "is_audited", "batch_qty", "stock_uom",
		],
		order_by="ifnull(last_audited, manufacturing_date) asc",
	)

	if not batches:
		return []

	batch_names = [b.name for b in batches]

	stock_values = frappe.get_all(
		"Stock Ledger Entry",
		filters={
			"batch_no": ["in", batch_names],
			"is_cancelled": 0,
		},
		fields=["batch_no", "sum(stock_value_difference) as stock_value"],
		group_by="batch_no",
	)
	stock_value_map = {row.batch_no: flt(row.stock_value) for row in stock_values}

	for b in batches:
		b.stock_value = stock_value_map.get(b.name, 0.0)

	return batches


def split_batches(batches):
	"""Split batches into (write_off, notify) by the auto write-off threshold."""
	write_off = [b for b in batches if b.stock_value < AUTO_WRITE_OFF_THRESHOLD]
	notify = [b for b in batches if b.stock_value >= AUTO_WRITE_OFF_THRESHOLD]
	return write_off, notify


def notify_raw_material_more_than_1_year(dry_run=False):
	batches = get_aged_raw_material_batches()
	if not batches:
		return frappe._dict({"written_off": [], "notified": [], "dry_run": dry_run})

	written_off, remaining = split_batches(batches)

	if written_off:
		auto_write_off_batches(written_off, dry_run=dry_run)

	if remaining and not dry_run:
		total_stock_value = sum(b.stock_value for b in remaining)
		doc_notif = frappe.get_doc("Notification", "Raw Material more than 1 year")
		doc = frappe._dict({
			"doc_list": remaining,
			"total_stock_value": total_stock_value,
		})
		doc_notif.send(doc)

	return frappe._dict({
		"written_off": len(written_off),
		"notified": len(remaining),
		"dry_run": dry_run,
	})


def get_write_off_stock(batch_names):
	"""Return per-(batch, warehouse) stock to scrap, grouped by company.

	Only positive balances in non-WIP warehouses are collected, mirroring the
	Scrap Request flow.
	"""
	if not batch_names:
		return {}

	wip_warehouse = get_wip_warehouse()

	rows = frappe.db.sql(
		"""
		SELECT
			sle.batch_no AS batch,
			b.item AS item_code,
			sle.warehouse,
			sle.company,
			SUM(sle.actual_qty) AS qty,
			i.stock_uom AS uom
		FROM `tabStock Ledger Entry` sle
		LEFT JOIN `tabBatch` b ON b.name = sle.batch_no
		LEFT JOIN `tabItem` i ON i.name = b.item
		WHERE
			sle.is_cancelled = 0
			AND sle.batch_no IN %(batches)s
			AND sle.warehouse NOT IN %(wip)s
		GROUP BY sle.batch_no, sle.warehouse
		HAVING qty > 0
		""",
		{"batches": tuple(batch_names), "wip": tuple(wip_warehouse) or ("",)},
		as_dict=1,
	)

	grouped = {}
	for row in rows:
		grouped.setdefault(row.company, []).append(row)
	return grouped


def auto_write_off_batches(batches, dry_run=False):
	"""Write off immaterial Raw Material batches via 'Scrap Materials' Stock Entries.

	Creates a single Stock Entry per company (one row per batch/warehouse) instead
	of one document per item, then disables every batch that was scrapped.
	"""
	batch_names = [b.name for b in batches]
	company_rows = get_write_off_stock(batch_names)

	if dry_run or not company_rows:
		return

	scrapped_batches = set()
	for company, rows in company_rows.items():
		try:
			make_scrap_stock_entry(company, rows)
			scrapped_batches.update(row.batch for row in rows)
		except Exception:
			frappe.log_error(
				title="Raw Material auto write-off failed",
				message=f"Company: {company}\nBatches: {[row.batch for row in rows]}\n{frappe.get_traceback()}",
			)

	for name in scrapped_batches:
		frappe.db.set_value("Batch", name, "disabled", 1)


def make_scrap_stock_entry(company, rows):
	"""Create and submit one 'Scrap Materials' Stock Entry for a company.

	`rows` is a list of dicts with batch, item_code, warehouse, qty and uom.
	"""
	switch_to_company_admin(company)

	scrap_account = frappe.db.get_value("Company", company, "account_for_raw_material_scrap")
	rnd_account = frappe.db.get_value("Company", company, "account_for_rnd_item_scrap")
	cost_center = frappe.db.get_value("Company", company, "cost_center")

	se = frappe.new_doc("Stock Entry")
	se.company = company
	se.stock_entry_type_view = WRITE_OFF_STOCK_ENTRY_TYPE
	se.purpose = "Material Issue"
	se.set_stock_entry_type()
	se.system_generated = 1
	se.remarks = "Raw Material older than 1 year, inventory value below threshold (system)"

	for row in rows:
		uom = row.get("uom") or frappe.get_cached_value("Item", row.item_code, "stock_uom")
		item_row = se.append("items")
		item_row.item_code = row.item_code
		item_row.qty = flt(row.qty, 7)
		item_row.uom = uom
		item_row.stock_uom = frappe.get_cached_value("Item", row.item_code, "stock_uom")
		item_row.batch_no = row.batch
		item_row.is_scrap_item = 1
		item_row.conversion_factor = get_conversion_factor(row.item_code, uom).get("conversion_factor", 1)
		item_row.s_warehouse = row.warehouse
		item_row.cost_center = cost_center
		if frappe.db.get_value("Item", row.item_code, "rnd_item"):
			item_row.expense_account = rnd_account or scrap_account
		else:
			item_row.expense_account = scrap_account

	se.set_missing_values()
	se.insert(ignore_permissions=1)
	se.submit()
	return se.name
