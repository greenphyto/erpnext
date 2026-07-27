# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Count, IfNull, Sum

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
			"label": _("Location Code"),
			"fieldname": "location_code",
			"fieldtype": "Link",
			"options": "Warehouse Location",
			"width": 160,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{"label": _("Aisle / Row"), "fieldname": "aisle_row", "fieldtype": "Data", "width": 100},
		{"label": _("Bay / Column"), "fieldname": "bay_column", "fieldtype": "Data", "width": 100},
		{"label": _("Level / Tier"), "fieldname": "level_tier", "fieldtype": "Data", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Batch Count"), "fieldname": "batch_count", "fieldtype": "Int", "width": 100},
		{"label": _("Total Qty"), "fieldname": "total_qty", "fieldtype": "Float", "width": 100},
		{
			"label": _("Mixed Storage Allowed"),
			"fieldname": "is_mixed_storage_allowed",
			"fieldtype": "Check",
			"width": 140,
		},
		{"label": _("Disabled"), "fieldname": "disabled", "fieldtype": "Check", "width": 90},
	]


def get_data(filters):
	wl = frappe.qb.DocType("Warehouse Location")
	bl = frappe.qb.DocType("Batch Location")

	query = (
		frappe.qb.from_(wl)
		.left_join(bl)
		.on(bl.warehouse_location == wl.name)
		.select(
			wl.name.as_("location_code"),
			wl.warehouse,
			wl.aisle_row,
			wl.bay_column,
			wl.level_tier,
			wl.status,
			wl.is_mixed_storage_allowed,
			wl.disabled,
			Count(bl.batch).distinct().as_("batch_count"),
			IfNull(Sum(bl.qty), 0).as_("total_qty"),
		)
		.groupby(wl.name)
		.orderby(wl.warehouse)
		.orderby(wl.aisle_row)
		.orderby(wl.bay_column)
		.orderby(wl.level_tier)
	)

	query = query.where(wl.warehouse == (filters.warehouse or get_default_warehouse()))

	if filters.status:
		query = query.where(wl.status == filters.status)
	if filters.aisle_row:
		query = query.where(wl.aisle_row.like(f"%{filters.aisle_row}%"))
	if filters.bay_column:
		query = query.where(wl.bay_column.like(f"%{filters.bay_column}%"))
	if filters.level_tier:
		query = query.where(wl.level_tier.like(f"%{filters.level_tier}%"))
	if not filters.show_disabled:
		query = query.where(wl.disabled == 0)
	if filters.batch:
		batch_locations = frappe.db.get_list(
			"Batch Location",
			filters={"batch": filters.batch, "qty": [">", 0]},
			pluck="warehouse_location",
		)
		query = query.where(wl.name.isin(batch_locations or [""]))

	return query.run(as_dict=True)
