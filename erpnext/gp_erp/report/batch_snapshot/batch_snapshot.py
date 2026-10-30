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

MY_CUSTOMER = "Greenphyto Tech Sdn Bhd"
KG_UOM = "Kg"


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
	item_codes = list({b.item_code for b in batches if b.item_code})

	manufacture_in_map, other_in_map = get_in_qty(batch_names, filters)
	draft_map = get_draft_qty(batch_names, filters)
	out_map = get_out_qty(batch_names, filters)
	distribution_map = get_distribution_qty(batch_names, item_codes)

	active_rows = []
	expired_rows = []

	for b in batches:
		suffix = TYPE_MAP.get(b.batch_type or "Default", "default")

		manufacture_in = flt(manufacture_in_map.get(b.batch_no))
		other_in = flt(other_in_map.get(b.batch_no))
		draft_by_suffix = draft_map.get(b.batch_no) or {}
		out_by_suffix = out_map.get(b.batch_no) or {}

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

		distribution = distribution_map.get(b.batch_no)
		if distribution:
			for dist_suffix, dist_qty in distribution.items():
				row["in_" + dist_suffix] += flt(dist_qty)
		else:
			row["in_" + suffix] += manufacture_in

		row["in_default"] += other_in

		for dsuffix, dqty in draft_by_suffix.items():
			row["draft_" + dsuffix] = flt(dqty)
		for osuffix, oqty in out_by_suffix.items():
			row["out_" + osuffix] = flt(oqty)

		row["left_default"] = row["in_default"] - row["draft_default"] - row["out_default"]
		row["left_my"] = row["in_my"] - row["draft_my"] - row["out_my"]
		row["left_no_pack"] = row["in_no_pack"] - row["draft_no_pack"] - row["out_no_pack"]

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


def get_distribution_qty(batch_names, item_codes):
	rows = frappe.db.sql(
		"""
		SELECT bdm.parent AS batch_no, bdm.packaging, bdm.qty
		FROM `tabBatch Distribution Mapping` bdm
		WHERE bdm.parenttype = 'Batch'
			AND bdm.parent IN %(batch_names)s
		""",
		{"batch_names": batch_names},
		as_dict=1,
	)
	if not rows:
		return {}

	packaging_customer = get_packaging_customer_map(item_codes)

	batch_item = {b: None for b in batch_names}
	dist_map = {}
	for d in rows:
		suffix = classify_packaging(d.packaging, packaging_customer)
		bucket = dist_map.setdefault(d.batch_no, {})
		bucket[suffix] = bucket.get(suffix, 0) + flt(d.qty)
	return dist_map


def get_packaging_customer_map(item_codes):
	if not item_codes:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT pla.packaging, pla.customer
		FROM `tabPackaging List Available` pla
		WHERE pla.parenttype = 'Item'
			AND pla.parent IN %(item_codes)s
			AND pla.packaging IS NOT NULL
		""",
		{"item_codes": item_codes},
		as_dict=1,
	)

	mapping = {}
	for d in rows:
		mapping.setdefault(d.packaging, set()).add(d.customer)
	return mapping


def classify_packaging(packaging, packaging_customer):
	if not packaging:
		return "no_pack"
	customers = packaging_customer.get(packaging) or set()
	if MY_CUSTOMER in customers:
		return "my"
	return "default"


def get_in_qty(batch_names, filters):
	conditions = ""
	if filters.get("company"):
		conditions += " AND sle.company = %(company)s"
	if filters.get("warehouse"):
		conditions += " AND sle.warehouse = %(warehouse)s"

	params = dict(filters)
	params["batch_names"] = batch_names

	rows = frappe.db.sql(
		"""
		SELECT
			sle.batch_no,
			CASE
				WHEN sle.voucher_type = 'Stock Entry' AND se.purpose = 'Manufacture'
				THEN 1 ELSE 0
			END AS is_manufacture,
			SUM(sle.actual_qty) AS qty
		FROM `tabStock Ledger Entry` sle
			LEFT JOIN `tabStock Entry` se
				ON sle.voucher_type = 'Stock Entry'
				AND se.name = sle.voucher_no
		WHERE IFNULL(sle.is_cancelled, 0) = 0
			AND sle.actual_qty > 0
			AND sle.batch_no IN %(batch_names)s
			{conditions}
		GROUP BY sle.batch_no, is_manufacture
		""".format(conditions=conditions),
		params,
		as_dict=1,
	)

	manufacture_map = {}
	other_map = {}
	for d in rows:
		target = manufacture_map if d.is_manufacture else other_map
		target[d.batch_no] = target.get(d.batch_no, 0) + flt(d.qty)
	return manufacture_map, other_map


def get_draft_qty(batch_names, filters):
	conditions = ""
	if filters.get("company"):
		conditions += " AND dn.company = %(company)s"
	if filters.get("warehouse"):
		conditions += " AND dni.warehouse = %(warehouse)s"

	params = dict(filters)
	params["batch_names"] = batch_names

	rows = frappe.db.sql(
		"""
		SELECT
			dni.batch_no,
			dn.customer AS customer,
			dni.uom AS uom,
			SUM(dni.stock_qty) AS qty
		FROM `tabDelivery Note` dn
			INNER JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
		WHERE dn.docstatus = 0
			AND dni.batch_no IN %(batch_names)s
			{conditions}
		GROUP BY dni.batch_no, dn.customer, dni.uom
		""".format(conditions=conditions),
		params,
		as_dict=1,
	)

	draft_map = {}
	for d in rows:
		suffix = classify_delivery(d.uom, d.customer)
		bucket = draft_map.setdefault(d.batch_no, {})
		bucket[suffix] = bucket.get(suffix, 0) + flt(d.qty)
	return draft_map


def get_out_qty(batch_names, filters):
	conditions = ""
	if filters.get("company"):
		conditions += " AND sle.company = %(company)s"
	if filters.get("warehouse"):
		conditions += " AND sle.warehouse = %(warehouse)s"

	params = dict(filters)
	params["batch_names"] = batch_names

	rows = frappe.db.sql(
		"""
		SELECT
			sle.batch_no,
			sle.voucher_type AS voucher_type,
			dn.customer AS customer,
			dni.uom AS uom,
			SUM(-sle.actual_qty) AS qty
		FROM `tabStock Ledger Entry` sle
			LEFT JOIN `tabDelivery Note Item` dni
				ON sle.voucher_type = 'Delivery Note'
				AND dni.name = sle.voucher_detail_no
			LEFT JOIN `tabDelivery Note` dn
				ON sle.voucher_type = 'Delivery Note'
				AND dn.name = sle.voucher_no
		WHERE IFNULL(sle.is_cancelled, 0) = 0
			AND sle.actual_qty < 0
			AND sle.batch_no IN %(batch_names)s
			{conditions}
		GROUP BY sle.batch_no, sle.voucher_type, dn.customer, dni.uom
		""".format(conditions=conditions),
		params,
		as_dict=1,
	)

	out_map = {}
	for d in rows:
		if d.voucher_type == "Delivery Note":
			suffix = classify_delivery(d.uom, d.customer)
		else:
			suffix = "default"
		bucket = out_map.setdefault(d.batch_no, {})
		bucket[suffix] = bucket.get(suffix, 0) + flt(d.qty)
	return out_map


def classify_delivery(uom, customer):
	if uom == KG_UOM:
		return "no_pack"
	if customer == MY_CUSTOMER:
		return "my"
	return "default"


def get_h_days(manufacturing_date):
	if not manufacturing_date:
		return ""
	days = date_diff(nowdate(), getdate(manufacturing_date))
	return "H+ {0}".format(days)
