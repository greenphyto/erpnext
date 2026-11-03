# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import cint, flt


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if not filters.company:
		frappe.throw(_("{0} is mandatory").format(_("Company")))
	if not filters.date:
		frappe.throw(_("{0} is mandatory").format(_("Date")))

	precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns()
	data = get_data(filters, precision)
	return columns, data


def get_columns():
	return [
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 160},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 160},
		{"label": _("Batch"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 180},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 70},
		{"label": _("Batch Rate"), "fieldname": "batch_rate", "fieldtype": "Currency", "width": 110},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Actual Value"), "fieldname": "actual_value", "fieldtype": "Currency", "width": 120},
		{"label": _("Difference"), "fieldname": "difference", "fieldtype": "Currency", "width": 120},
		{"label": _("Avg Rate"), "fieldname": "avg_rate", "fieldtype": "Currency", "width": 110},
	]


def get_warehouse_condition(filters, alias="sle"):
	if not filters.get("warehouse"):
		return "", {}
	lft, rgt = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"])
	cond = (
		f" and exists (select wh.name from `tabWarehouse` wh "
		f"where wh.lft >= %(wh_lft)s and wh.rgt <= %(wh_rgt)s and wh.name = {alias}.warehouse)"
	)
	return cond, {"wh_lft": lft, "wh_rgt": rgt}


def get_current_batch_balance(filters, precision):
	"""Balance qty and actual stock value per item/warehouse/batch as of the given date."""
	conditions = ""
	values = {"date": filters.date, "company": filters.company}

	wh_cond, wh_values = get_warehouse_condition(filters)
	conditions += wh_cond
	values.update(wh_values)

	if filters.get("item_code"):
		conditions += " and sle.item_code = %(item_code)s"
		values["item_code"] = filters.item_code

	if filters.get("item_group"):
		conditions += " and item.item_group = %(item_group)s"
		values["item_group"] = filters.item_group

	rows = frappe.db.sql(
		f"""
		select
			sle.item_code,
			sle.warehouse,
			sle.batch_no,
			sum(sle.actual_qty) as qty,
			sum(sle.stock_value_difference) as actual_value
		from `tabStock Ledger Entry` sle
		inner join `tabItem` item on item.name = sle.item_code
		where sle.docstatus < 2
			and sle.is_cancelled = 0
			and sle.company = %(company)s
			and ifnull(sle.batch_no, '') != ''
			and sle.posting_date <= %(date)s
			{conditions}
		group by sle.item_code, sle.warehouse, sle.batch_no
		having round(qty, {precision}) != 0
		""",
		values,
		as_dict=True,
	)
	return rows


def get_batch_rates(batch_item_pairs):
	"""Batch rate = incoming_rate of the first incoming SLE (actual_qty > 0) for each batch,
	e.g. the rate when the batch first entered via Stock Entry (Manufacture), Purchase Receipt, etc."""
	rates = {}
	if not batch_item_pairs:
		return rates

	batch_nos = list({b for (_i, _w, b) in batch_item_pairs})
	rows = frappe.db.sql(
		"""
		select sle.item_code, sle.warehouse, sle.batch_no, sle.incoming_rate, sle.posting_date,
			sle.posting_time, sle.creation
		from `tabStock Ledger Entry` sle
		where sle.docstatus < 2
			and sle.is_cancelled = 0
			and sle.actual_qty > 0
			and sle.batch_no in %(batch_nos)s
		order by sle.posting_date asc, sle.posting_time asc, sle.creation asc
		""",
		{"batch_nos": batch_nos},
		as_dict=True,
	)
	for r in rows:
		key = (r.item_code, r.warehouse, r.batch_no)
		if key not in rates:
			rates[key] = flt(r.incoming_rate)
	return rates


def get_data(filters, precision):
	balances = get_current_batch_balance(filters, precision)
	if not balances:
		return []

	item_names = {}
	item_uoms = {}
	for d in frappe.db.sql("""select name, item_name, stock_uom from `tabItem`""", as_dict=True):
		item_names[d.name] = d.item_name
		item_uoms[d.name] = d.stock_uom

	pairs = [(b.item_code, b.warehouse, b.batch_no) for b in balances]
	batch_rates = get_batch_rates(pairs)

	grouped = {}
	for b in balances:
		grouped.setdefault((b.item_code, b.warehouse), []).append(b)

	data = []
	for (item_code, warehouse) in sorted(grouped.keys()):
		rows = sorted(grouped[(item_code, warehouse)], key=lambda x: x.batch_no or "")
		total_qty = 0.0
		total_amount = 0.0
		for b in rows:
			rate = batch_rates.get((item_code, warehouse, b.batch_no), 0.0)
			qty = flt(b.qty, precision)
			amount = flt(qty * rate, precision)
			actual_value = flt(b.actual_value, precision)
			difference = flt(amount - actual_value, precision)
			total_qty += qty
			total_amount += amount
			data.append(
				{
					"item_code": item_code,
					"item_name": item_names.get(item_code, ""),
					"warehouse": warehouse,
					"batch_no": b.batch_no,
					"qty": qty,
					"stock_uom": item_uoms.get(item_code, ""),
					"batch_rate": rate,
					"amount": amount,
					"actual_value": actual_value,
					"difference": difference,
				}
			)

		avg_rate = flt(total_amount / total_qty, precision) if total_qty else 0.0
		data.append(
			{
				"item_code": item_code,
				"item_name": item_names.get(item_code, ""),
				"warehouse": warehouse,
				"batch_no": None,
				"qty": flt(total_qty, precision),
				"stock_uom": item_uoms.get(item_code, ""),
				"batch_rate": None,
				"amount": flt(total_amount, precision),
				"avg_rate": avg_rate,
				"is_group_total": 1,
			}
		)
		data.append({})

	return data


@frappe.whitelist()
def make_stock_reconciliation(filters):
	"""Build an unsaved Stock Reconciliation for batches whose actual stock value
	differs from qty x batch rate. Returns the mapped doc dict for the client to route to."""
	if isinstance(filters, str):
		filters = json.loads(filters)
	filters = frappe._dict(filters)

	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))
	if not filters.get("date"):
		frappe.throw(_("{0} is mandatory").format(_("Date")))

	precision = cint(frappe.db.get_default("float_precision")) or 3

	balances = get_current_batch_balance(filters, precision)
	if not balances:
		frappe.throw(_("No stock balance found for the given filters"))

	pairs = [(b.item_code, b.warehouse, b.batch_no) for b in balances]
	batch_rates = get_batch_rates(pairs)

	doc = frappe.new_doc("Stock Reconciliation")
	doc.company = filters.get("company")
	doc.purpose = "Stock Reconciliation"
	doc.posting_date = filters.get("date")

	diff_count = 0
	for b in balances:
		rate = batch_rates.get((b.item_code, b.warehouse, b.batch_no), 0.0)
		qty = flt(b.qty, precision)
		amount = flt(qty * rate, precision)
		actual_value = flt(b.actual_value, precision)
		if flt(amount - actual_value, precision) == 0:
			continue

		diff_count += 1
		doc.append(
			"items",
			{
				"item_code": b.item_code,
				"warehouse": b.warehouse,
				"batch_no": b.batch_no,
				"qty": qty,
				"valuation_rate": rate,
			},
		)

	if not diff_count:
		frappe.throw(_("No batch with a stock value difference was found"))

	return doc.as_dict()
