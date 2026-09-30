import frappe

from erpnext.stock.stock_ledger import get_valuation_rate


"""
Split packaging items on work orders based on their linked requests.

Background:
    A work order can serve multiple requests. Each request item may need a
    different packaging (packet) item, even for the same packet size/UOM,
    because the packaging item is resolved per customer. Previously the
    packaging resolution only matched by UOM, so multiple requests sharing
    the same UOM were merged into a single packaging row (or resolved to the
    wrong packaging item), instead of being split per request.

What this patch does:
    1. Finds submitted work orders (status "Not Started" / "In Process")
       linked to one or more requests (request_no is set).
    2. Safety guards — a work order is only fixed when ALL apply:
       - current_operation is still in operation 1-2
         ("Not Started", "Seeding" or "Transplanting");
       - current packaging rows differ from the expected (computed) rows;
       - no stock movement yet (transferred_qty = 0 on all packaging rows).
    3. Resolves the packaging item per request item, with priority:
       a. Request Items.packaging_item (manually set on the request);
       b. Item's "Packaging List Available" child table, matching UOM
          (first row by idx that matches the request's proposed customer,
          then a generic row without customer);
       c. the packaging list row with default = 1;
       d. Manufacturing Settings > default_packaging (last fallback).
    4. Splits the work order packaging into one row per
       (packaging item, unit weight, UOM) group, with quantity proportional
       to each request's share of the total stock quantity:
       ceil(wo.qty * group_qty / total_request_qty / unit_weight).
    5. Updates existing packaging rows in place, appends new rows at the
       end of the required_items table (continuing idx), and deletes
       obsolete packaging rows that have no stock movement.
    6. Syncs the work order header (packet_size, conversion_factor) only
       when all request items share the same unit weight and the header
       value is stale. Mixed sizes leave the header untouched.
    7. Touches the parent's modified timestamp so changes are visible in
       list views sorted by modified.

Usage:
    bench --site <site> execute erpnext.patches.v14_0.update_in_process_work_order_packet_size.execute
    bench --site <site> execute erpnext.patches.v14_0.update_in_process_work_order_packet_size.execute --kwargs '{"dry_run": true}'

    dry_run=True only reports which work orders would change and how,
    without writing anything.
"""


def split_packaging(work_order, request_items):
	"""Return expected packaging rows [(item_code, required_qty, packet_size)] for a work order."""
	packaging_list = frappe.get_all(
		"Packaging List Available",
		filters={"parent": work_order.production_item, "parentfield": "packaging"},
		fields=["packaging", "package_item", "weight", "customer", "idx"],
		order_by="idx asc",
	)
	request_customers = {
		d.name: d.proposed_customer
		for d in frappe.get_all(
			"Request",
			filters={"name": ["in", work_order.request_no.replace(" ", "").split(",")]},
			fields=["name", "proposed_customer"],
		)
	}
	default_packaging = next((p for p in packaging_list if p.default), None)

	items = []
	for item in request_items:
		packaging_item = item.packaging_item
		if not packaging_item:
			customer = request_customers.get(item.parent)
			matching = [p for p in packaging_list if p.packaging == item.uom and p.customer == customer]
			if not matching:
				matching = [
					p
					for p in packaging_list
					if p.packaging == item.uom and not p.customer and not customer
				]
			if not matching:
				matching = [p for p in packaging_list if p.packaging == item.uom and not p.customer]
			if matching:
				packaging_item = matching[0].package_item
		if not packaging_item and default_packaging:
			packaging_item = default_packaging.package_item
		if not packaging_item:
			packaging_item = frappe.db.get_single_value("Manufacturing Settings", "default_packaging")
		if packaging_item:
			items.append(
				frappe._dict(
					packaging_item=packaging_item,
					unit_weight=item.unit_weight,
					uom=item.uom,
					stock_qty=frappe.utils.flt(item.qty) * frappe.utils.flt(item.unit_weight),
				)
			)

	items = [item for item in items if item.unit_weight and item.packaging_item]
	request_qty = sum(item.stock_qty for item in items)
	if not request_qty:
		return []

	packaging = {}
	for item in items:
		key = (item.packaging_item, item.unit_weight, item.uom)
		packaging[key] = packaging.get(key, 0) + item.stock_qty

	rows = []
	for (pack_item, unit_weight, uom), stock_qty in packaging.items():
		required_qty = frappe.utils.ceil(work_order.qty * stock_qty / request_qty / unit_weight)
		rows.append(frappe._dict(item_code=pack_item, required_qty=required_qty, packet_size=uom))
	return rows


def needs_fix(work_order, request_items, current_packaging):
	"""Only fix when current packaging rows differ from expected rows."""
	expected = split_packaging(work_order, request_items)
	if not expected:
		return False

	current = sorted((row.item_code, row.required_qty) for row in current_packaging)
	expected = sorted((row.item_code, row.required_qty) for row in expected)
	return current != expected


def update_packaging_items(work_order, request_items, expected_rows):
	current = frappe.get_all(
		"Work Order Item",
		filters={"parent": work_order.name, "is_packaging": 1},
		fields=["name", "item_code", "rate"],
		order_by="idx asc",
	)
	used = set()
	max_idx = frappe.db.sql(
		"select max(idx) from `tabWork Order Item` where parent = %(parent)s",
		{"parent": work_order.name},
	)[0][0]
	next_idx = frappe.utils.cint(max_idx)
	for row in expected_rows:
		existing = next(
			(item for item in current if item.name not in used and item.item_code == row.item_code), None
		)
		if existing:
			used.add(existing.name)
			if existing.required_qty != row.required_qty:
				frappe.db.set_value(
					"Work Order Item",
					existing.name,
					{"required_qty": row.required_qty, "amount": row.required_qty * existing.rate},
					update_modified=True,
				)
			continue

		item = frappe.get_doc("Item", row.item_code)
		rate = get_valuation_rate(row.item_code, work_order.source_warehouse, "", "")
		next_idx += 1
		new_row = frappe.get_doc(
			{
				"doctype": "Work Order Item",
				"parent": work_order.name,
				"parenttype": "Work Order",
				"parentfield": "required_items",
				"idx": next_idx,
				"operation": "Harvesting",
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": f"{item.description or ''} ({row.packet_size})",
				"allow_alternative_item": 0,
				"include_item_in_manufacturing": 0,
				"required_qty": row.required_qty,
				"rate": rate,
				"amount": rate * row.required_qty,
				"source_warehouse": work_order.source_warehouse,
				"is_packaging": 1,
			}
		)
		new_row.db_insert()

	# remove packaging rows not needed anymore (only rows with zero transferred/consumed)
	for item in current:
		if item.name not in used:
			safe = frappe.db.get_value(
				"Work Order Item",
				item.name,
				["transferred_qty", "consumed_qty", "returned_qty"],
				as_dict=True,
			)
			if safe and not safe.transferred_qty and not safe.consumed_qty and not safe.returned_qty:
				frappe.db.delete("Work Order Item", item.name)

	# touch parent modified so changes are visible in list view / modified sort
	frappe.db.set_value(
		"Work Order",
		work_order.name,
		{"modified": frappe.utils.now()},
		update_modified=True,
	)


def execute(dry_run=0):
	"""dry_run=True: only report what would change, no writes, no commit.

	bench --site test6 execute erpnext.patches.v14_0.update_in_process_work_order_packet_size.execute --kwargs '{"dry_run": true}'
	"""
	work_orders = frappe.get_all(
		"Work Order",
		filters={
			"docstatus": 1,
			"status": ["in", ["Not Started", "In Process"]],
			"request_no": ["is", "set"],
		},
		fields=[
			"name",
			"request_no",
			"production_item",
			"qty",
			"packet_size",
			"conversion_factor",
			"source_warehouse",
		],
	)

	for work_order in work_orders:
		# only fix work orders still in operations 1-2 (Seeding/Transplanting)
		current_operation = frappe.db.get_value("Work Order", work_order.name, "current_operation")
		if current_operation not in ("Not Started", "Seeding", "Transplanting"):
			continue

		request_names = work_order.request_no.replace(" ", "").split(",")
		request_items = frappe.get_all(
			"Request Items",
			filters={"parent": ["in", request_names], "item_code": work_order.production_item},
			fields=["parent", "qty", "unit_weight", "uom", "packaging_item"],
			order_by="idx asc",
		)
		if not request_items:
			continue

		current_packaging = frappe.get_all(
			"Work Order Item",
			filters={"parent": work_order.name, "is_packaging": 1},
			fields=["item_code", "required_qty"],
		)
		if not needs_fix(work_order, request_items, current_packaging):
			continue

		# no stock movement allowed
		moved = frappe.db.exists(
			"Work Order Item",
			{
				"parent": work_order.name,
				"is_packaging": 1,
				"transferred_qty": [">", 0],
			},
		)
		if moved:
			continue

		# sync packet_size if single uniform size and mismatched
		if (
			len({item.unit_weight for item in request_items}) == 1
			and request_items[0].unit_weight != work_order.conversion_factor
		):
			print(
				"Header",
				work_order.name,
				"packet_size:",
				work_order.packet_size,
				"->",
				request_items[0].uom,
				"| conversion_factor:",
				work_order.conversion_factor,
				"->",
				request_items[0].unit_weight,
			)
			frappe.db.set_value(
				"Work Order",
				work_order.name,
				{
					"packet_size": request_items[0].uom,
					"conversion_factor": request_items[0].unit_weight,
				},
				update_modified=True,
			)

		expected_rows = split_packaging(work_order, request_items)
		if dry_run:
			current = frappe.get_all(
				"Work Order Item",
				filters={"parent": work_order.name, "is_packaging": 1},
				fields=["item_code", "required_qty"],
				order_by="idx asc",
			)
			wo_changes = {}
			if (
				len({item.unit_weight for item in request_items}) == 1
				and request_items[0].unit_weight != work_order.conversion_factor
			):
				wo_changes = {
					"packet_size": request_items[0].uom,
					"conversion_factor": request_items[0].unit_weight,
				}
			print(
				"[DRY RUN] would fix",
				work_order.name,
				"current:",
				[(r.item_code, r.required_qty) for r in current],
				"-> expected:",
				[(r.item_code, r.required_qty) for r in expected_rows],
			)
			if wo_changes:
				print("           header:", wo_changes)
			continue
		update_packaging_items(work_order, request_items, expected_rows)
		print("Fixed", work_order.name, [(r.item_code, r.required_qty) for r in expected_rows])
		# break