import frappe
from frappe.utils import getdate
from erpnext.controllers.foms import get_wip_warehouse
from erpnext.setup.doctype.company.company import switch_to_company_admin


def execute():
	scrap_expired_raw_material_below_1kg()


def scrap_expired_raw_material_below_1kg():
	wip_warehouse = get_wip_warehouse()

	data = frappe.db.sql("""
		SELECT *
		FROM (
			SELECT
				sle.batch_no AS batch,
				b.item,
				sle.warehouse,
				sle.company,
				SUM(sle.actual_qty) AS batch_qty,
				b.expiry_date,
				sle.stock_uom AS uom
			FROM `tabStock Ledger Entry` sle
			LEFT JOIN `tabBatch` b ON b.name = sle.batch_no
			LEFT JOIN `tabItem` i ON i.name = sle.item_code
			WHERE
				sle.is_cancelled = 0
				AND sle.batch_no IS NOT NULL
				AND sle.batch_no != ''
				AND sle.warehouse NOT IN %(wh)s
				AND b.expiry_date <= %(exp)s
				AND i.item_group = 'Raw Material'
			GROUP BY sle.batch_no, sle.warehouse
			ORDER BY sle.company, b.expiry_date ASC
		) a
		WHERE a.batch_qty > 0 AND a.batch_qty < 1
	""", {"wh": wip_warehouse, "exp": getdate()}, as_dict=1, debug=0)

	if not data:
		print("No expired raw material batches below 1 kg found.")
		return

	print(f"Found {len(data)} expired raw material batch(es) below 1 kg. Creating Stock Entry...")

	companys = list(set([d.company for d in data]))
	result = {}

	for company in companys:
		switch_to_company_admin(company)

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.company = company
		stock_entry.stock_entry_type_view = "Scrap Materials"
		stock_entry.purpose = "Material Issue"
		stock_entry.set_stock_entry_type()
		expense_account = frappe.db.get_value("Company", company, "account_for_raw_material_scrap")
		cost_center = frappe.db.get_value("Company", company, "cost_center")

		for d in data:
			if d.company != company:
				continue
			row = stock_entry.append("items")
			row.item_code = d.item
			row.qty = d.batch_qty
			row.uom = d.uom
			row.batch_no = d.batch
			row.is_scrap_item = 1
			row.conversion_factor = 1
			row.s_warehouse = d.warehouse
			row.expense_account = expense_account
			row.cost_center = cost_center

		stock_entry.system_generated = 1
		stock_entry.remarks = "Scrap expired raw material below 1 kg (patch)"
		stock_entry.set_missing_values()
		stock_entry.insert(ignore_permissions=1)
		# stock_entry.submit()

		result[company] = stock_entry.name
		print(f"  Company: {company} -> Stock Entry: {stock_entry.name}")

	frappe.db.commit()
	print("Done.")
	return result
