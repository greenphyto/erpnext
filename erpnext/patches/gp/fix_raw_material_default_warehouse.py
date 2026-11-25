import frappe


def execute(dry_run=False):
	rows = frappe.db.sql("""
		SELECT d.name, d.parent AS item_code, d.company, d.default_warehouse
		FROM `tabItem Default` d
		INNER JOIN `tabItem` i ON i.name = d.parent
		WHERE i.item_group = 'Raw Material'
		ORDER BY d.company, d.parent
	""", as_dict=1)

	print(f"Dry run: {bool(dry_run)}, total rows: {len(rows)}")

	stores = {}
	updated = skipped = no_store = 0
	for row in rows:
		if row.company not in stores:
			stores[row.company] = frappe.db.get_value(
				"Warehouse",
				{"company": row.company, "warehouse_name": "Stores", "is_group": 0},
				"name",
			)
		target = stores[row.company]

		if not target:
			no_store += 1
			print(f"[NO STORES] {row.item_code} | {row.company}")
			continue

		if row.default_warehouse == target:
			skipped += 1
			print(f"[OK] {row.item_code} | {row.company} | {row.default_warehouse}")
			continue

		print(f"[{'WOULD UPDATE' if dry_run else 'UPDATE'}] {row.item_code} | {row.company} | {row.default_warehouse} -> {target}")
		if not dry_run:
			frappe.db.set_value("Item Default", row.name, "default_warehouse", target, update_modified=False)
		updated += 1

	if not dry_run:
		frappe.db.commit()

	print(f"Updated: {updated}, already ok: {skipped}, no Stores warehouse: {no_store}")
