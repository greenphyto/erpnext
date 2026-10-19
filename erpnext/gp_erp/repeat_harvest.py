import frappe
from frappe.utils import add_days


def generate_repeat_harvest_work_orders(doc, method=""):
	"""Called via doc_events on Work Order on_submit.
	Checks if production_item has an active Repeat Harvest Group,
	then generates child Work Orders for each configured harvest item."""

	# Skip if this WO is itself a child of a repeat harvest
	if doc.repeat_harvest_group:
		return

	# Find active Repeat Harvest Group for this item
	rhg_name = frappe.db.get_value(
		"Repeat Harvest Group",
		{"parent_item": doc.production_item, "is_active": 1},
		"name",
	)
	if not rhg_name:
		return

	rhg = frappe.get_doc("Repeat Harvest Group", rhg_name)

	# Get Repeat Harvest Items for this group
	rhi_items = frappe.get_all(
		"Repeat Harvest Item",
		filters={"repeat_harvest_group": rhg_name},
		fields=["name", "item", "sequence", "harvest_date_offset", "status"],
		order_by="sequence asc",
	)

	if not rhi_items:
		return

	base_date = doc.planned_start_date

	for rhi_data in rhi_items:
		# Skip if already planned or beyond
		if rhi_data.status in ("Planned", "In Progress", "Completed"):
			continue

		# Calculate planned start date
		if rhi_data.harvest_date_offset:
			planned_date = add_days(base_date, rhi_data.harvest_date_offset)
		else:
			planned_date = add_days(base_date, rhg.harvest_gap_in_days * rhi_data.sequence)

		# Get default BOM for child item
		bom = frappe.db.get_value(
			"BOM", {"item": rhi_data.item, "is_active": 1, "is_default": 1}, "name"
		)

		if not bom:
			frappe.log_error(
				message=f"No default BOM found for item {rhi_data.item}",
				title="Repeat Harvest WO Generation",
			)
			continue

		# Create child Work Order
		child_wo = frappe.new_doc("Work Order")
		child_wo.update(
			{
				"production_item": rhi_data.item,
				"bom_no": bom,
				"qty": doc.qty,
				"company": doc.company,
				"fg_warehouse": doc.fg_warehouse,
				"wip_warehouse": doc.wip_warehouse,
				"scrap_warehouse": doc.scrap_warehouse,
				"planned_start_date": planned_date,
				"repeat_harvest_group": rhg_name,
				"repeat_harvest_item": rhi_data.name,
				"harvest_sequence": rhi_data.sequence,
				"parent_harvest_product": doc.production_item,
			}
		)

		child_wo.set_required_items()
		child_wo.insert(ignore_permissions=True)
		child_wo.submit()

		# Update Repeat Harvest Item with WO link and status
		frappe.db.set_value(
			"Repeat Harvest Item",
			rhi_data.name,
			{
				"work_order": child_wo.name,
				"planned_harvest_date": planned_date,
				"qty": doc.qty,
				"uom": doc.stock_uom,
				"status": "Planned",
			},
		)


def handle_wo_cancellation(doc, method=""):
	"""Called via doc_events on Work Order on_cancel.
	Updates linked Repeat Harvest Item status to Cancelled."""
	if doc.repeat_harvest_item:
		frappe.db.set_value(
			"Repeat Harvest Item", doc.repeat_harvest_item, "status", "Cancelled"
		)
