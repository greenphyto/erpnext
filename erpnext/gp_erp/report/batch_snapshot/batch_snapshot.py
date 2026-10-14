# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, date_diff

TYPE_MAP = {
	"Default": "default",
	"Export": "my",
	"No Pack": "no_pack",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "item_name", "label": _("Product Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "item_code", "label": _("Product ID"), "fieldtype": "Link", "options": "Item", "width": 130},
		{"fieldname": "foms_id", "label": _("FOMS ID"), "fieldtype": "Data", "width": 110},
		{"fieldname": "batch_no", "label": _("Batch ID"), "fieldtype": "Link", "options": "Batch", "width": 160},
		{"fieldname": "in_default", "label": _("IN (default)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "in_my", "label": _("IN (MY)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "in_no_pack", "label": _("IN (No Pack)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "draft_default", "label": _("DRAFT (Default)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "draft_my", "label": _("DRAFT (MY)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "draft_no_pack", "label": _("DRAFT (No Pack)"), "fieldtype": "Float", "width": 130},
		{"fieldname": "out_default", "label": _("OUT (default)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "out_my", "label": _("OUT (MY)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "out_no_pack", "label": _("OUT (No Pack)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "left_default", "label": _("LEFT (default)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "left_my", "label": _("LEFT (MY)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "left_no_pack", "label": _("LEFT (No Pack)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "h_days", "label": _("H+ Days"), "fieldtype": "Data", "width": 90},
	]


def get_conditions(filters):
	conditions = ["b.item_group = 'Products'"]
	if filters.get("item_code"):
		conditions.append("b.item = %(item_code)s")
	return " AND " + " AND ".join(conditions)


def get_data(filters):
	conditions = get_conditions(filters)

	batches = frappe.db.sql(
		"""
		SELECT
			b.name AS batch_no,
			b.item AS item_code,
			b.item_name AS item_name,
			b.foms_lot_id AS foms_id,
			b.batch_type AS batch_type,
			b.status AS status,
			COALESCE(b.manufacturing_date, DATE(b.creation)) AS manufacturing_date
		FROM `tabBatch` b
		WHERE IFNULL(b.disabled, 0) = 0 {conditions}
		ORDER BY COALESCE(b.manufacturing_date, DATE(b.creation)) DESC, b.creation DESC
		""".format(conditions=conditions),
		filters,
		as_dict=1,
	)

	if not batches:
		return []

	batch_names = [b.batch_no for b in batches]

	in_map = get_in_qty(batch_names, filters)
	draft_map, out_map = get_delivery_qty(batch_names, filters)

	active_rows = []
	expired_rows = []

	for b in batches:
		suffix = TYPE_MAP.get(b.batch_type or "Default", "default")

		in_qty = flt(in_map.get(b.batch_no))
		draft_qty = flt(draft_map.get(b.batch_no))
		out_qty = flt(out_map.get(b.batch_no))
		left_qty = in_qty - draft_qty - out_qty

		row = {
			"item_name": b.item_name,
			"item_code": b.item_code,
			"foms_id": b.foms_id,
			"batch_no": b.batch_no,
			"in_default": 0, "in_my": 0, "in_no_pack": 0,
			"draft_default": 0, "draft_my": 0, "draft_no_pack": 0,
			"out_default": 0, "out_my": 0, "out_no_pack": 0,
			"left_default": 0, "left_my": 0, "left_no_pack": 0,
			"h_days": get_h_days(b.manufacturing_date),
		}
		row["in_" + suffix] = in_qty
		row["draft_" + suffix] = draft_qty
		row["out_" + suffix] = out_qty
		row["left_" + suffix] = left_qty

		if b.status == "Expired":
			expired_rows.append(row)
		else:
			active_rows.append(row)

	data = []
	data.extend(active_rows)
	if active_rows and expired_rows:
		data.append({})
	data.extend(expired_rows)

	return data


def get_in_qty(batch_names, filters):
	conditions = ""
	if filters.get("company"):
		conditions += " AND se.company = %(company)s"
	if filters.get("warehouse"):
		conditions += " AND sed.t_warehouse = %(warehouse)s"

	params = dict(filters)
	params["batch_names"] = batch_names

	rows = frappe.db.sql(
		"""
		SELECT sed.batch_no, SUM(sed.qty) AS qty
		FROM `tabStock Entry` se
			INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		WHERE se.docstatus = 1
			AND se.purpose = 'Manufacture'
			AND IFNULL(sed.is_finished_item, 0) = 1
			AND sed.batch_no IN %(batch_names)s
			{conditions}
		GROUP BY sed.batch_no
		""".format(conditions=conditions),
		params,
		as_dict=1,
	)
	return {d.batch_no: flt(d.qty) for d in rows}


def get_delivery_qty(batch_names, filters):
	conditions = ""
	if filters.get("company"):
		conditions += " AND dn.company = %(company)s"
	if filters.get("warehouse"):
		conditions += " AND dni.warehouse = %(warehouse)s"

	params = dict(filters)
	params["batch_names"] = batch_names

	rows = frappe.db.sql(
		"""
		SELECT dni.batch_no, dn.docstatus AS docstatus, SUM(dni.stock_qty) AS qty
		FROM `tabDelivery Note` dn
			INNER JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
		WHERE dn.docstatus < 2
			AND dni.batch_no IN %(batch_names)s
			{conditions}
		GROUP BY dni.batch_no, dn.docstatus
		""".format(conditions=conditions),
		params,
		as_dict=1,
	)

	draft_map = {}
	out_map = {}
	for d in rows:
		if d.docstatus == 0:
			draft_map[d.batch_no] = draft_map.get(d.batch_no, 0) + flt(d.qty)
		elif d.docstatus == 1:
			out_map[d.batch_no] = out_map.get(d.batch_no, 0) + flt(d.qty)
	return draft_map, out_map


def get_h_days(manufacturing_date):
	if not manufacturing_date:
		return ""
	days = date_diff(nowdate(), getdate(manufacturing_date))
	return "H+ {0}".format(days)
