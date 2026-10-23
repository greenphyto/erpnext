# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Batch"),
			"fieldname": "batch_no",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 160,
		},
		{
			"label": _("Item"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Lot ID"),
			"fieldname": "foms_lot_id",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Creation Date"),
			"fieldname": "creation_date",
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"label": _("Expiry Date"),
			"fieldname": "expiry_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 90,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
	]


def get_data(filters):
	batch_conditions = {"disabled": 0}
	if filters.get("item"):
		batch_conditions["item"] = filters.get("item")
	elif filters.get("item_group"):
		items = frappe.get_all(
			"Item",
			filters={"item_group": filters.get("item_group")},
			pluck="name",
		)
		batch_conditions["item"] = ["in", items or [""]]

	if filters.get("show_only_active_batch"):
		batch_conditions["expiry_date"] = [">=", nowdate()]

	batches = frappe.get_all(
		"Batch",
		filters=batch_conditions,
		fields=[
			"name as batch_no",
			"item",
			"item_name",
			"foms_lot_id",
			"creation as creation_date",
			"expiry_date",
			"stock_uom",
		],
	)

	if not batches:
		return []

	batch_names = [b.batch_no for b in batches]
	qty_map = get_batch_qty_map(batch_names, filters)

	data = []
	for b in batches:
		qty = qty_map.get(b.batch_no)

		if filters.get("warehouse") and qty is None:
			continue

		b.qty = qty or 0
		if not b.qty:
			b.status = "Empty"
		elif b.expiry_date and getdate(b.expiry_date) < getdate(nowdate()):
			b.status = "Expired"
		else:
			b.status = "Active"
		data.append(b)

	data.sort(
		key=lambda d: (
			d.item or "",
			-(get_datetime(d.creation_date).timestamp() if d.creation_date else 0),
		)
	)

	return data


def get_batch_qty_map(batch_names, filters):
	conditions = {"is_cancelled": 0, "batch_no": ["in", batch_names]}
	if filters.get("warehouse"):
		conditions["warehouse"] = filters.get("warehouse")
	if filters.get("company"):
		conditions["company"] = filters.get("company")

	rows = frappe.get_all(
		"Stock Ledger Entry",
		filters=conditions,
		fields=["batch_no", "sum(actual_qty) as qty"],
		group_by="batch_no",
	)

	return {r.batch_no: r.qty for r in rows}
