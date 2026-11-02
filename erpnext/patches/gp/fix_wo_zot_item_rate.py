import frappe
from frappe.utils import flt

from erpnext.stock.stock_ledger import get_valuation_rate

# bench --site erp-prod execute erpnext.patches.gp.fix_wo_zot_item_rate.execute
def execute():
	rows = frappe.db.sql(
		"""
		SELECT
			wi.name AS wo_item,
			wi.parent AS work_order,
			wi.item_code,
			wi.rate,
			wi.required_qty,
			wi.source_warehouse
		FROM
			`tabWork Order Item` wi
		WHERE
			wi.rate > 50
			AND wi.item_code LIKE 'RM-ZOT-%%'
		""",
		as_dict=1,
	)

	print("found", len(rows), "ZOT work order item(s) with rate > 50")

	for row in rows:
		warehouse = "Finished Goods - GPL"
		if not warehouse:
			print("skip (no source_warehouse)", row.work_order, row.item_code, "rate", row.rate)
			continue

		new_rate = get_valuation_rate(
			row.item_code,
			warehouse,
			"Work Order",
			row.work_order,
			raise_error_if_no_rate=False,
		)

		if not new_rate:
			print("skip (no valuation rate)", row.work_order, row.item_code, "wh", warehouse, "rate", row.rate)
			continue

		if flt(new_rate) == flt(row.rate):
			print("skip (same rate)", row.work_order, row.item_code, "rate", row.rate, "val", new_rate)
			continue

		new_amount = flt(new_rate) * flt(row.required_qty)
		frappe.db.set_value(
			"Work Order Item",
			row.wo_item,
			{"rate": new_rate, "amount": new_amount},
			update_modified=False,
		)
		frappe.get_doc("Work Order", row.work_order).add_comment(
			"Comment",
			text=f"rate updated from anomaly ZOT rate ({row.item_code}: {flt(row.rate)} -> {flt(new_rate)})",
		)
		print("updated", row.work_order, row.item_code, "rate", row.rate, "->", new_rate)

	frappe.db.commit()
