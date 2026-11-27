import frappe

from erpnext.buying.doctype.request.request import get_part_number_group

OLD_ITEM = "PR-LV-BLI"
NEW_ITEM = "PR-LV-BLJ"
MIN_DELIVERY_DATE = "2027-01-01"

# bench --site erp-prod execute erpnext.patches.gp.replace_request_item_bli_to_blj.execute
def execute(dry_run=0):
	for item in (OLD_ITEM, NEW_ITEM):
		if not frappe.db.exists("Item", item):
			print("Item {0} not found".format(item))
			return

	new_item = frappe.db.get_value(
		"Item",
		NEW_ITEM,
		["item_name", "lead_time_days", "default_bom", "salad_product"],
		as_dict=True,
	)

	rows = frappe.db.sql(
		"""
		SELECT ri.name, ri.parent, ri.uom, ri.item_code, r.proposed_customer, r.docstatus
		FROM `tabRequest Items` ri
		INNER JOIN `tabRequest` r ON r.name = ri.parent
		WHERE ri.parenttype = 'Request'
			AND ri.item_code = %(old)s
			AND r.delivery_date >= %(date)s
		""",
		{"old": OLD_ITEM, "date": MIN_DELIVERY_DATE},
		as_dict=True,
	)

	if not rows:
		print("No Request Items with {0} found".format(OLD_ITEM))
		return

	print("{0} Request Items found".format(len(rows)))

	parents = set()
	for row in rows:
		parents.add(row.parent)
		print("{0} / {1} (docstatus {2})".format(row.parent, row.item_code, row.docstatus))

		if dry_run:
			continue

		frappe.db.set_value(
			"Request Items",
			row.name,
			{
				"item_code": NEW_ITEM,
				"item_name": new_item.item_name,
				"lead_time_days": new_item.lead_time_days or 0,
				"is_salad_product": new_item.salad_product or 0,
				"salad_recipe": new_item.default_bom,
				"part_number_group": get_part_number_group(
					NEW_ITEM, row.uom, row.proposed_customer
				),
			},
			update_modified=False,
		)

	if dry_run:
		print("Dry run: {0} Requests would change".format(len(parents)))
		return

	for parent in parents:
		frappe.db.set_value("Request", parent, "modified", frappe.utils.now(), update_modified=False)

	frappe.db.commit()
	print("Replaced {0} -> {1} in {2} Requests".format(OLD_ITEM, NEW_ITEM, len(parents)))
