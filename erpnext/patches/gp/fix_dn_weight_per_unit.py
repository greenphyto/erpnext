import frappe
from frappe.utils import flt

"""
Fix Delivery Note items where weight_per_unit does not match conversion_factor.

Since every stock UOM is kg, weight_per_unit (weight of 1 unit of the transaction
UOM, in kg) must equal conversion_factor (stock qty per 1 unit of the transaction
UOM). This patch repairs the mismatched rows *in place* (no cancel/amend):

  1. find Delivery Note Items where weight_per_unit != conversion_factor
  2. set weight_per_unit = conversion_factor
  3. recompute total_weight = weight_per_unit * qty
  4. persist with a direct DB update (weight fields do not affect GL / stock ledger)

Usage:
  bench --site erp-prod execute erpnext.patches.gp.fix_dn_weight_per_unit.execute
  bench --site test6 execute "erpnext.patches.gp.fix_dn_weight_per_unit.execute --kwargs \"{'dry_run': True}\""
  bench --site erp-prod execute "erpnext.patches.gp.fix_dn_weight_per_unit.execute --kwargs \"{'delivery_note': 'DO-2026-04756'}\""
"""


def execute(delivery_note=None, dry_run=0):
	mode = "DRY RUN (no changes will be committed)" if dry_run else "APPLY"
	print("=== fix_dn_weight_per_unit: {0} ===".format(mode))

	dni = frappe.qb.DocType("Delivery Note Item")
	dn = frappe.qb.DocType("Delivery Note")

	query = (
		frappe.qb.from_(dni)
		.inner_join(dn)
		.on(dn.name == dni.parent)
		.select(
			dni.name,
			dni.parent,
			dni.item_code,
			dni.qty,
			dni.conversion_factor,
			dni.weight_per_unit,
			dni.total_weight,
		)
		.where(dn.docstatus == 1)
		.where(dn.posting_date >= "2026-01-01")
		.orderby(dn.posting_date, order=frappe.qb.desc)
	)

	if delivery_note:
		query = query.where(dni.parent == delivery_note)

	rows = query.run(as_dict=True)

	print("Total Delivery Note Item scanned: {0}".format(len(rows)))

	fixed = 0
	for row in rows:
		cf = flt(row.conversion_factor)
		wpu = flt(row.weight_per_unit)

		if wpu == cf:
			continue

		if dry_run and fixed >= 100:
			print("=== DRY RUN limit reached: stopping at 100 records ===")
			break

		new_total_weight = flt(cf * flt(row.qty))

		print(
			"{0} / {1} ({2}): weight_per_unit {3} -> {4}, total_weight {5} -> {6}".format(
				row.parent,
				row.name,
				row.item_code,
				wpu,
				cf,
				flt(row.total_weight),
				new_total_weight,
			)
		)

		if not dry_run:
			frappe.db.set_value(
				"Delivery Note Item",
				row.name,
				{
					"weight_per_unit": cf,
					"total_weight": new_total_weight,
				},
				update_modified=False,
			)

		fixed += 1

	if dry_run:
		print("=== DRY RUN finished: {0} item(s) would be updated, nothing committed ===".format(fixed))
	else:
		frappe.db.commit()
		print("=== APPLY finished: {0} item(s) updated ===".format(fixed))
