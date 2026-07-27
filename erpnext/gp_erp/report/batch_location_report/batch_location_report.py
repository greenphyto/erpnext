# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.stock.doctype.warehouse_location_settings.warehouse_location_settings import (
	get_default_warehouse,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Batch"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 140,
		},
		{"label": _("Batch ID"), "fieldname": "batch_id", "fieldtype": "Data", "width": 140},
		{
			"label": _("Item"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
		{
			"label": _("Warehouse Location"),
			"fieldname": "warehouse_location",
			"fieldtype": "Link",
			"options": "Warehouse Location",
			"width": 160,
		},
		{"label": _("Aisle / Row"), "fieldname": "aisle_row", "fieldtype": "Data", "width": 100},
		{"label": _("Bay / Column"), "fieldname": "bay_column", "fieldtype": "Data", "width": 100},
		{"label": _("Level / Tier"), "fieldname": "level_tier", "fieldtype": "Data", "width": 100},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
		{"label": _("Last Updated"), "fieldname": "last_updated", "fieldtype": "Datetime", "width": 150},
	]


def get_data(filters):
	bl = frappe.qb.DocType("Batch Location")
	wl = frappe.qb.DocType("Warehouse Location")
	batch = frappe.qb.DocType("Batch")
	item = frappe.qb.DocType("Item")

	query = (
		frappe.qb.from_(bl)
		.inner_join(wl)
		.on(wl.name == bl.warehouse_location)
		.inner_join(batch)
		.on(batch.name == bl.batch)
		.inner_join(item)
		.on(item.name == bl.item)
		.select(
			bl.batch,
			batch.batch_id.as_("batch_id"),
			bl.item,
			item.item_name,
			bl.warehouse_location,
			wl.aisle_row,
			wl.bay_column,
			wl.level_tier,
			bl.warehouse,
			bl.qty,
			bl.stock_uom,
			bl.last_updated,
		)
		.where(bl.qty > 0)
		.orderby(bl.batch)
		.orderby(bl.warehouse_location)
	)

	query = query.where(bl.warehouse == (filters.warehouse or get_default_warehouse()))

	if filters.batch:
		query = query.where(bl.batch == filters.batch)
	if filters.item:
		query = query.where(bl.item == filters.item)
	if filters.warehouse_location:
		query = query.where(bl.warehouse_location == filters.warehouse_location)
	if filters.aisle_row:
		query = query.where(wl.aisle_row.like(f"%{filters.aisle_row}%"))
	if filters.bay_column:
		query = query.where(wl.bay_column.like(f"%{filters.bay_column}%"))
	if filters.level_tier:
		query = query.where(wl.level_tier.like(f"%{filters.level_tier}%"))

	return query.run(as_dict=True)
