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
			"label": _("Warehouse Action"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Warehouse Action",
			"width": 140,
		},
		{"label": _("Posting Datetime"), "fieldname": "posting_datetime", "fieldtype": "Datetime", "width": 160},
		{"label": _("Action Type"), "fieldname": "action_type", "fieldtype": "Data", "width": 90},
		{
			"label": _("Batch"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 140,
		},
		{
			"label": _("Item"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{
			"label": _("From Location"),
			"fieldname": "from_location",
			"fieldtype": "Link",
			"options": "Warehouse Location",
			"width": 140,
		},
		{
			"label": _("To Location"),
			"fieldname": "to_location",
			"fieldtype": "Link",
			"options": "Warehouse Location",
			"width": 140,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150,
		},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
		{"label": _("Stock Qty"), "fieldname": "stock_qty", "fieldtype": "Float", "width": 90},
		{
			"label": _("User"),
			"fieldname": "user",
			"fieldtype": "Link",
			"options": "User",
			"width": 140,
		},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 150},
	]


def get_data(filters):
	wa = frappe.qb.DocType("Warehouse Action")

	query = (
		frappe.qb.from_(wa)
		.select(
			wa.name,
			wa.posting_datetime,
			wa.action_type,
			wa.batch,
			wa.item,
			wa.from_location,
			wa.to_location,
			wa.warehouse,
			wa.qty,
			wa.uom,
			wa.stock_qty,
			wa.user,
			wa.remarks,
		)
		.where(wa.docstatus == 1)
		.orderby(wa.posting_datetime, order=frappe.qb.desc)
	)

	query = query.where(wa.warehouse == (filters.warehouse or get_default_warehouse()))

	if filters.action_type:
		query = query.where(wa.action_type == filters.action_type)
	if filters.batch:
		query = query.where(wa.batch == filters.batch)
	if filters.item:
		query = query.where(wa.item == filters.item)
	if filters.warehouse_location:
		query = query.where(
			(wa.from_location == filters.warehouse_location)
			| (wa.to_location == filters.warehouse_location)
		)
	if filters.user:
		query = query.where(wa.user == filters.user)
	if filters.from_date:
		query = query.where(wa.posting_datetime >= filters.from_date)
	if filters.to_date:
		query = query.where(wa.posting_datetime <= f"{filters.to_date} 23:59:59")

	return query.run(as_dict=True)
