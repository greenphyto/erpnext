import frappe
from erpnext.setup.doctype.company.company import switch_to_company_admin

def execute(dry_run=0):
	return transfer_raw_material_to_stores(dry_run=dry_run)

def transfer_raw_material_to_stores(dry_run=0):
	dry_run = int(dry_run)
	tag = "[DRY RUN] " if dry_run else ""

	data = frappe.db.sql("""
		SELECT
			sle.item_code,
			sle.warehouse,
			sle.company,
			IFNULL(sle.batch_no, '') AS batch_no,
			sle.stock_uom AS uom,
			SUM(sle.actual_qty) AS qty
		FROM `tabStock Ledger Entry` sle
		INNER JOIN `tabItem` i ON i.name = sle.item_code
		INNER JOIN `tabWarehouse` w ON w.name = sle.warehouse
		WHERE
			sle.is_cancelled = 0
			AND i.item_group = 'Raw Material'
			AND w.warehouse_name = 'Finished Goods'
		GROUP BY sle.item_code, sle.warehouse, IFNULL(sle.batch_no, '')
		HAVING qty > 0
		ORDER BY sle.company, sle.item_code
	""", as_dict=1)

	if not data:
		print("No Raw Material stock in Finished Goods found.")
		return

	result = {}
	for company in sorted(set(d.company for d in data)):
		to_warehouse = frappe.db.get_value(
			"Warehouse", {"company": company, "warehouse_name": "Stores", "is_group": 0}, "name"
		)
		if not to_warehouse:
			print(f"{tag}Company: {company} | Stores warehouse not found, skipped")
			continue

		print(f"{tag}Company: {company} | To: {to_warehouse}")
		switch_to_company_admin(company)

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.company = company
		stock_entry.purpose = "Material Transfer"
		stock_entry.set_stock_entry_type()

		for d in data:
			if d.company != company:
				continue
			print(
				f"  {tag}{d.item_code} | batch: {d.batch_no or '-'} | qty: {d.qty} {d.uom} | "
				f"{d.warehouse} -> {to_warehouse}"
			)
			row = stock_entry.append("items")
			row.item_code = d.item_code
			row.qty = d.qty
			row.uom = d.uom
			row.stock_uom = d.uom
			row.conversion_factor = 1
			row.s_warehouse = d.warehouse
			row.t_warehouse = to_warehouse
			if d.batch_no:
				row.batch_no = d.batch_no

		if dry_run:
			print(f"  {tag}Would create draft Stock Entry with {len(stock_entry.items)} item(s)")
			continue

		stock_entry.system_generated = 1
		stock_entry.remarks = "Transfer Raw Material from Finished Goods to Stores (patch)"
		stock_entry.set_missing_values()
		stock_entry.insert(ignore_permissions=1)

		result[company] = stock_entry.name
		print(f"  Created draft Stock Entry: {stock_entry.name}")

	if not dry_run:
		frappe.db.commit()
	return result
