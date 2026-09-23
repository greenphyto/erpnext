import frappe


"""
bench --site erp-prod execute erpnext.patches.v14_0.update_in_process_work_order_packet_size.execute
"""
def update_packaging_items(work_order, request_items):
	request_qty = sum(item.qty * item.unit_weight for item in request_items if item.unit_weight)
	if not request_qty:
		return

	packaging_qty = {}
	for item in request_items:
		if item.packaging_item and item.unit_weight:
			stock_qty = item.qty * item.unit_weight
			key = (item.packaging_item, item.unit_weight, item.uom)
			packaging_qty[key] = packaging_qty.get(key, 0) + stock_qty

	items = frappe.get_all(
		"Work Order Item",
		filters={"parent": work_order.name, "is_packaging": 1},
		fields=["name", "item_code", "rate"],
		order_by="idx asc",
	)
	used = set()
	for packaging_item, unit_weight, uom in packaging_qty:
		required_qty = work_order.qty * packaging_qty[(packaging_item, unit_weight, uom)] / request_qty / unit_weight
		row = next((item for item in items if item.name not in used and item.item_code == packaging_item), None)
		if row:
			used.add(row.name)
			frappe.db.set_value(
				"Work Order Item",
				row.name,
				{"required_qty": required_qty, "amount": required_qty * row.rate},
				update_modified=False,
			)
			continue

		work_order_doc = frappe.get_doc("Work Order", work_order.name)
		item = frappe.get_doc("Item", packaging_item)
		rate = get_valuation_rate(item.item_code, work_order.source_warehouse, "", "")
		row = work_order_doc.append(
			"required_items",
			{
				"rate": rate,
				"amount": rate * required_qty,
				"operation": "Harvesting",
				"item_code": packaging_item,
				"item_name": item.item_name,
				"description": item.description,
				"required_qty": required_qty,
				"source_warehouse": work_order.source_warehouse,
				"is_packaging": 1,
			},
		)
		row.db_insert()


def execute():
	work_orders = frappe.get_all(
		"Work Order",
		filters={"docstatus": 1, "status": "In Process", "request_no": ["is", "set"]},
		fields=["name", "request_no", "production_item", "qty", "packet_size", "conversion_factor"],
	)


	for work_order in work_orders:
		if work_order.name != "26-1408-001":
			continue

		request_names = work_order.request_no.replace(" ", "").split(",")
		request_items = frappe.get_all(
			"Request Items",
			filters={"parent": ["in", request_names], "item_code": work_order.production_item},
			fields=["uom", "unit_weight", "packaging_item", "qty"],
			order_by="idx asc",
		)

		print(request_names, request_items)

		if not request_items:
			continue
		request_item = request_items[0]

		if len({item.unit_weight for item in request_items}) == 1 and request_item.unit_weight != work_order.conversion_factor:
			print("Work order", work_order.name, work_order.production_item, work_order.conversion_factor, request_item.unit_weight)
			frappe.db.set_value(
				"Work Order",
				work_order.name,
				{
					"packet_size": request_item.uom,
					"conversion_factor": request_item.unit_weight,
				},
				update_modified=False,
			)

		update_packaging_items(work_order, request_items)
