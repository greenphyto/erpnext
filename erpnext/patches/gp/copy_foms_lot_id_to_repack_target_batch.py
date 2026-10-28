import frappe


"""
bench --site erp-prod execute erpnext.patches.gp.copy_foms_lot_id_to_repack_target_batch.execute
"""
def execute():
	copy_foms_lot_id_to_repack_target_batch()


def copy_foms_lot_id_to_repack_target_batch(dry_run=0):
	"""Backfill foms_lot_id on target (finished) batches of auto item-change Repack entries.

	For existing auto-generated Repack Stock Entries (created by
	create_item_change_repack), the finished item's batch was created without
	copying foms_lot_id from the consumed source batch. Since the mapping is
	1-on-1, copy the source batch's foms_lot_id onto the target batch.

	Pass dry_run=True to only print what would change without writing.
	"""
	print(f"Backfilling foms_lot_id on repack target batches... (dry_run={dry_run})")

	repacks = frappe.get_all(
		"Stock Entry",
		filters={"name": ["in", frappe.get_all("Stock Entry", filters={"auto_repack": ["is", "set"]}, pluck="auto_repack")]},
		pluck="name",
	)

	updated = 0
	for se_name in repacks:
		rows = frappe.get_all(
			"Stock Entry Detail",
			filters={"parent": se_name},
			fields=["is_finished_item", "s_warehouse", "t_warehouse", "batch_no"],
		)

		source_batch = None
		target_batch = None
		for row in rows:
			if row.is_finished_item and row.t_warehouse:
				target_batch = row.batch_no
			elif row.s_warehouse and not row.t_warehouse:
				source_batch = row.batch_no

		if not source_batch or not target_batch:
			print(f"[SKIP] {se_name}: source_batch={source_batch}, target_batch={target_batch}")
			continue

		source_lot = frappe.db.get_value("Batch", source_batch, "foms_lot_id")
		if not source_lot:
			print(f"[SKIP] {se_name}: source batch {source_batch} has no foms_lot_id")
			continue

		target_lot = frappe.db.get_value("Batch", target_batch, "foms_lot_id")
		if target_lot:
			print(f"[SKIP] {se_name}: target batch {target_batch} already has foms_lot_id={target_lot}")
			continue

		if dry_run:
			print(f"[DRY RUN] {se_name}: would set target batch {target_batch} foms_lot_id={source_lot} (from {source_batch})")
		else:
			frappe.db.set_value("Batch", target_batch, "foms_lot_id", source_lot)
			print(f"[UPDATE] {se_name}: set target batch {target_batch} foms_lot_id={source_lot} (from {source_batch})")
		updated += 1

	if not dry_run:
		frappe.db.commit()

	print(f"foms_lot_id backfill done. {'Would update' if dry_run else 'Updated'} {updated} target batches.")
