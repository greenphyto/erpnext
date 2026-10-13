import csv
import os

import frappe
from frappe.utils import flt


def execute():
	# only work orders that actually ran a Manufacture entry, otherwise
	# "actual consumed" is zero and the comparison is meaningless
	wos = frappe.get_all(
		"Work Order",
		filters={"docstatus": 1, "produced_qty": [">", 0]},
		fields=["name", "production_item", "qty", "produced_qty", "bom_no", "status", "creation"],
		order_by="creation desc",
		limit_page_length=50,
	)

	if not wos:
		print("No work orders found")
		return

	wo_names = [w.name for w in wos]

	# BOM-driven required qty per WO item (already scaled to WO qty)
	bom_rows = frappe.db.sql(
		"""
		SELECT parent AS work_order, item_code, uom,
			SUM(required_qty) AS required_qty
		FROM `tabWork Order Item`
		WHERE parent IN %(wo_names)s
		GROUP BY parent, item_code, uom
		""",
		{"wo_names": wo_names},
		as_dict=1,
	)
	required_map = {}
	for r in bom_rows:
		required_map[(r.work_order, r.item_code)] = r

	# actual consumed raw-material qty from the Manufacture stock entry
	# (exclude finished-good and scrap rows: those have no source warehouse)
	actual_rows = frappe.db.sql(
		"""
		SELECT se.work_order, sed.item_code, sed.uom,
			SUM(sed.qty) AS actual_qty,
			SUM(sed.basic_amount) AS actual_amount
		FROM `tabStock Entry` se
			INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		WHERE se.docstatus = 1
			AND se.purpose = 'Manufacture'
			AND se.work_order IN %(wo_names)s
			AND sed.s_warehouse IS NOT NULL
			AND sed.s_warehouse != ''
			AND IFNULL(sed.is_finished_item, 0) = 0
			AND IFNULL(sed.is_scrap_item, 0) = 0
		GROUP BY se.work_order, sed.item_code, sed.uom
		""",
		{"wo_names": wo_names},
		as_dict=1,
	)
	actual_map = {}
	for r in actual_rows:
		actual_map[(r.work_order, r.item_code)] = r

	wo_info = {w.name: w for w in wos}

	keys = set(required_map.keys()) | set(actual_map.keys())

	results = []
	for work_order, item_code in sorted(keys):
		req = required_map.get((work_order, item_code))
		act = actual_map.get((work_order, item_code))

		required_qty = flt(req.required_qty) if req else 0
		actual_qty = flt(act.actual_qty) if act else 0
		diff_qty = actual_qty - required_qty
		diff_pct = (diff_qty / required_qty * 100) if required_qty else (100 if actual_qty else 0)

		w = wo_info.get(work_order)
		results.append(
			{
				"work_order": work_order,
				"production_item": w.production_item if w else "",
				"wo_qty": flt(w.qty) if w else 0,
				"produced_qty": flt(w.produced_qty) if w else 0,
				"bom_no": w.bom_no if w else "",
				"item_code": item_code,
				"uom": (req.uom if req else (act.uom if act else "")),
				"bom_required_qty": required_qty,
				"actual_consumed_qty": actual_qty,
				"diff_qty": diff_qty,
				"diff_pct": round(diff_pct, 2),
				"actual_amount": flt(act.actual_amount) if act else 0,
			}
		)

	out_dir = frappe.get_site_path("private", "files")
	os.makedirs(out_dir, exist_ok=True)
	out_path = os.path.join(out_dir, "wo_bom_vs_actual_discrepancy.csv")

	fieldnames = [
		"work_order",
		"production_item",
		"wo_qty",
		"produced_qty",
		"bom_no",
		"item_code",
		"uom",
		"bom_required_qty",
		"actual_consumed_qty",
		"diff_qty",
		"diff_pct",
		"actual_amount",
	]

	with open(out_path, "w", newline="") as f:
		writer = csv.DictWriter(f, fieldnames=fieldnames)
		writer.writeheader()
		writer.writerows(results)

	print("Exported {0} rows for {1} work orders to:".format(len(results), len(wos)))
	print(os.path.abspath(out_path))
