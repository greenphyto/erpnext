import frappe
from frappe.utils import add_days


def generate_repeat_harvest_work_orders(doc, method=""):
	"""Called via doc_events on Work Order on_submit.
	Checks if production_item has an active Repeat Harvest Group,
	then generates child Work Orders for each configured harvest item."""

	# Skip if the Repeat Harvest feature is not installed on this site
	if not frappe.db.exists("DocType", "Repeat Harvest Group"):
		return

	# Skip if this WO is itself a child of a repeat harvest
	if doc.get("repeat_harvest_group"):
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

	# Auto-generate Repeat Harvest Items from the group template if missing
	ensure_repeat_harvest_items(rhg)

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

		# Get default BOM for the child item (source recipe)
		child_bom = frappe.db.get_value(
			"BOM", {"item": rhi_data.item, "is_active": 1, "is_default": 1}, "name"
		)

		if not child_bom:
			frappe.log_error(
				message=f"No default BOM found for item {rhi_data.item}",
				title="Repeat Harvest WO Generation",
			)
			continue

		# Build a bridge BOM that produces the parent item using the child's recipe
		bom = get_or_create_bridge_bom(doc.production_item, rhi_data.item, child_bom)

		# Create the sequence Work Order: output = parent, raw material = child's recipe
		child_wo = frappe.new_doc("Work Order")
		child_wo.update(
			{
				"production_item": doc.production_item,
				"bom_no": bom,
				"qty": doc.qty,
				"gross_weight": doc.gross_weight or doc.qty,
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


def get_or_create_bridge_bom(parent_item, child_item, child_bom_name):
	"""Return a BOM that produces `parent_item` using `child_item`'s recipe.

	The bridge BOM is a copy of the child's default BOM with the output item
	switched to the parent. It is reused across Work Orders (get-or-create),
	is never marked as default, and leaves the parent's own default BOM untouched.
	Costs are recalculated by ERPNext from the copied items/operations."""

	existing = frappe.db.get_value(
		"BOM",
		{
			"item": parent_item,
			"copy_from": child_item,
			"is_active": 1,
			"docstatus": 1,
		},
		"name",
	)
	if existing:
		return existing

	bridge = frappe.copy_doc(frappe.get_doc("BOM", child_bom_name))
	bridge.item = parent_item
	bridge.is_default = 0
	bridge.is_active = 1
	bridge.copy_from = child_item
	# Avoid colliding with the child's FOMS recipe version / default-naming logic
	if bridge.meta.has_field("foms_recipe_version"):
		bridge.foms_recipe_version = None
	bridge.insert(ignore_permissions=True)
	bridge.submit()
	return bridge.name


def ensure_repeat_harvest_items(rhg):
	"""Create Repeat Harvest Items from the group's harvest_items template
	for any child item that does not yet have a Repeat Harvest Item in the group.
	Existing Repeat Harvest Items are left untouched."""
	template_rows = rhg.get("harvest_items", [])
	if not template_rows:
		return

	existing_items = set(
		frappe.get_all(
			"Repeat Harvest Item",
			filters={"repeat_harvest_group": rhg.name},
			pluck="item",
		)
	)

	for row in template_rows:
		if row.item in existing_items:
			continue

		rhi = frappe.new_doc("Repeat Harvest Item")
		rhi.update(
			{
				"repeat_harvest_group": rhg.name,
				"item": row.item,
				"sequence": row.sequence,
				"harvest_date_offset": row.harvest_date_offset,
				"status": "Draft",
			}
		)
		rhi.insert(ignore_permissions=True)
		existing_items.add(row.item)


def handle_wo_cancellation(doc, method=""):
	"""Called via doc_events on Work Order on_cancel.
	Updates linked Repeat Harvest Item status to Cancelled."""
	if doc.repeat_harvest_item:
		frappe.db.set_value(
			"Repeat Harvest Item", doc.repeat_harvest_item, "status", "Cancelled"
		)
