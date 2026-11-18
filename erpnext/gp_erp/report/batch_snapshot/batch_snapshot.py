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
			b.reference_doctype AS reference_doctype,
			b.reference_name AS reference_name,
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

	manufacture_in_map, other_in_map = get_in_qty(batch_names, filters)
	draft_map = get_draft_qty(batch_names, filters)
	out_map = get_out_qty(batch_names, filters)
	ratio_map = get_request_ratio_map(batches)

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

		ratio = ratio_map.get(b.batch_no)
		if ratio:
			for ratio_suffix, ratio_value in ratio.items():
				row["in_" + ratio_suffix] += manufacture_in * ratio_value
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


def get_request_ratio_map(batches):
	stock_entries = {
		b.batch_no: b.reference_name
		for b in batches
		if b.reference_doctype == "Stock Entry" and b.reference_name
	}
	if not stock_entries:
		return {}

	se_wo = dict(
		frappe.db.sql(
			"""
			SELECT name, work_order FROM `tabStock Entry`
			WHERE name IN %(names)s AND IFNULL(work_order, '') != ''
			""",
			{"names": list(set(stock_entries.values()))},
		)
	)
	wo_names = list(set(se_wo.values()))
	if not wo_names:
		return {}

	wo_request = dict(
		frappe.db.sql(
			"""
			SELECT name, request_no FROM `tabWork Order`
			WHERE name IN %(names)s AND IFNULL(request_no, '') != ''
			""",
			{"names": wo_names},
		)
	)

	all_requests = set()
	wo_requests = {}
	for wo, request_no in wo_request.items():
		names = [r.strip() for r in request_no.split(",") if r.strip()]
		wo_requests[wo] = names
		all_requests.update(names)
	if not all_requests:
		return {}

	item_by_batch = {b.batch_no: b.item_code for b in batches}

	request_rows = frappe.db.sql(
		"""
		SELECT
			req.name AS request,
			ri.item_code,
			SUM(IFNULL(ri.qty, 0) * IF(IFNULL(ri.unit_weight, 0) > 0, ri.unit_weight, 1)) AS weight,
			IF(cust.represents_company = %(company)s, 1, 0) AS is_my
		FROM `tabRequest` req
			INNER JOIN `tabRequest Items` ri ON ri.parent = req.name
			LEFT JOIN `tabCustomer` cust ON cust.name = req.proposed_customer
		WHERE req.name IN %(requests)s
		GROUP BY req.name, ri.item_code, is_my
		""",
		{"requests": list(all_requests), "company": MY_CUSTOMER},
		as_dict=1,
	)
	weights = {}
	for r in request_rows:
		weights.setdefault((r.request, r.item_code), (flt(r.weight), r.is_my))

	ratio_map = {}
	for batch_no, se in stock_entries.items():
		wo = se_wo.get(se)
		if not wo:
			continue
		totals = {"my": 0, "default": 0}
		for req in wo_requests.get(wo, []):
			weight, is_my = weights.get((req, item_by_batch.get(batch_no)), (0, 0))
			totals["my" if is_my else "default"] += weight
		grand = totals["my"] + totals["default"]
		if grand <= 0:
			continue
		ratio_map[batch_no] = {k: v / grand for k, v in totals.items() if v}
	return ratio_map


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
