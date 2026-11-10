import frappe
from frappe.utils import add_days, flt, today

from erpnext.stock.doctype.batch.batch import get_batch_qty
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

# Batches with an inventory value below this threshold are written off
# automatically, without R&D validation, as testing them costs more than
# their immaterial value.
AUTO_WRITE_OFF_THRESHOLD = 100.0


def get_context(context):
	pass


def get_aged_raw_material_batches():
	"""Return aged Raw Material batches, each annotated with its stock value."""
	one_year_ago = add_days(today(), -365)

	batches = frappe.get_all(
		"Batch",
		filters={
			"item_group": "Raw Material",
			"batch_qty": [">", 0],
			"manufacturing_date": ["<=", one_year_ago],
			"disabled": 0,
			# batch with expiry_date is considered already curated by user, skip it
			"expiry_date": ["is", "not set"],
		},
		fields=["name", "item", "item_name", "item_group", "manufacturing_date", "batch_qty", "stock_uom"],
		order_by="manufacturing_date asc",
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

	for b in written_off:
		auto_write_off_batch(b, dry_run=dry_run)

	if remaining and not dry_run:
		total_stock_value = sum(b.stock_value for b in remaining)
		doc_notif = frappe.get_doc("Notification", "Raw Material more than 1 year")
		doc = frappe._dict({
			"doc_list": remaining,
			"total_stock_value": total_stock_value,
		})
		doc_notif.send(doc)

	return frappe._dict({
		"written_off": written_off,
		"notified": remaining,
		"dry_run": dry_run,
	})


def auto_write_off_batch(batch, dry_run=False):
	"""Write off an immaterial Raw Material batch via a Material Issue Stock Entry.

	Creates one submitted Stock Entry per warehouse that still holds qty for the
	batch, then disables the batch.
	"""
	warehouse_qtys = get_batch_qty(batch_no=batch.name)
	if not isinstance(warehouse_qtys, list):
		return

	for row in warehouse_qtys:
		qty = flt(row.get("qty"))
		if qty <= 0:
			continue

		if dry_run:
			continue

		try:
			make_stock_entry(
				item_code=batch.item,
				qty=qty,
				from_warehouse=row.get("warehouse"),
				batch_no=batch.name,
				purpose="Material Issue",
			)
		except Exception:
			frappe.log_error(
				title="Raw Material auto write-off failed",
				message=f"Batch: {batch.name}, Warehouse: {row.get('warehouse')}, Qty: {qty}\n{frappe.get_traceback()}",
			)
			return

	if not dry_run:
		frappe.db.set_value("Batch", batch.name, "disabled", 1)
