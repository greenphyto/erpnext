# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "work_order", "label": _("Work Order"), "fieldtype": "Link", "options": "Work Order", "width": 130},
		{"fieldname": "posting_date", "label": _("Completed On"), "fieldtype": "Date", "width": 100},
		{"fieldname": "item_code", "label": _("Crop"), "fieldtype": "Link", "options": "Item", "width": 130},
		{"fieldname": "item_name", "label": _("Crop Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 90},
		{"fieldname": "gross_qty", "label": _("Gross Qty (kg)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "saleable_qty", "label": _("Saleable Qty (kg)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "loss_qty", "label": _("Loss Qty (kg)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "loss_pct", "label": _("Loss %"), "fieldtype": "Percent", "width": 80},
		{"fieldname": "material_cost", "label": _("Material Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "manpower_rate", "label": _("Manpower Rate/kg"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "manpower_cost", "label": _("Manpower Cost"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "utilities_rate", "label": _("Utilities Rate/kg"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "utilities_cost", "label": _("Utilities Cost"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "total_cost", "label": _("Total Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "cost_per_kg", "label": _("Cost per kg"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "selling_price", "label": _("Selling Price/kg"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "sales_value", "label": _("Sales Value"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "profit", "label": _("Profit/(Loss)"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "profit_pct", "label": _("Profit %"), "fieldtype": "Percent", "width": 90},
	]


def get_conditions(filters):
	conditions = ["wo.docstatus = 1"]
	if filters.get("company"):
		conditions.append("wo.company = %(company)s")
	# attribute each work order to its completion month (when FG and cost land)
	if filters.get("from_date"):
		conditions.append("wo.actual_end_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("wo.actual_end_date <= %(to_date)s")
	if filters.get("work_order"):
		conditions.append("wo.name = %(work_order)s")
	if filters.get("item_code"):
		conditions.append("wo.production_item = %(item_code)s")
	if not filters.get("show_in_progress"):
		conditions.append("wo.status IN ('Completed', 'Stopped')")

	return " AND ".join(conditions)


def get_data(filters):
	conditions = get_conditions(filters)

	# work orders with rate card rates (Harvesting operation)
	wos = frappe.db.sql(
		"""
		SELECT
			wo.name AS work_order,
			wo.production_item AS item_code,
			i.item_name AS item_name,
			wo.status,
			wo.qty AS gross_qty,
			wo.produced_qty AS saleable_qty,
			wo.actual_start_date,
			wo.actual_end_date,
			rcd.manpower AS manpower_rate,
			rcd.electricity AS utilities_rate
		FROM `tabWork Order` wo
			INNER JOIN `tabItem` i ON i.name = wo.production_item
			LEFT JOIN `tabRate Card` rc ON rc.name = i.rate_card
			LEFT JOIN `tabRate Card Detail` rcd ON rcd.parent = rc.name
				AND rcd.operation = 'Harvesting'
		WHERE {conditions}
		ORDER BY wo.name DESC
		""".format(conditions=conditions),
		filters,
		as_dict=1,
	)

	if not wos:
		return []

	wo_names = [d.work_order for d in wos]

	# actual material cost: outgoing value of the Manufacture stock entry only
	# (Material Transfer entries feed WIP and would double count)
	se_costs = frappe.db.sql(
		"""
		SELECT work_order, SUM(total_outgoing_value) AS material_cost
		FROM `tabStock Entry`
		WHERE docstatus = 1 AND purpose = 'Manufacture' AND work_order IN %(wo_names)s
		GROUP BY work_order
		""",
		{"wo_names": wo_names},
		as_dict=1,
	)
	material_map = {d.work_order: flt(d.material_cost) for d in se_costs}

	# last selling price per kg from latest submitted Sales Invoice
	# SI rate is per sales UOM; convert to item stock uom (kg) via conversion_factor
	item_prices = frappe.db.sql(
		"""
		SELECT sii.item_code,
			sii.rate / IF(sii.conversion_factor > 0, sii.conversion_factor, 1) AS price_per_stock_uom
		FROM `tabSales Invoice Item` sii
			INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
		WHERE si.docstatus = 1 AND si.is_return = 0
			AND sii.item_code IN %(item_codes)s
			AND sii.rate > 0
		ORDER BY si.posting_date DESC, si.name DESC
		""",
		{"item_codes": list({d.item_code for d in wos})},
		as_dict=1,
	)
	price_map = {}
	for d in item_prices:
		price_map.setdefault(d.item_code, flt(d.price_per_stock_uom))

	data = []
	for d in wos:
		saleable_qty = flt(d.saleable_qty)
		gross_qty = flt(d.gross_qty)
		loss_qty = gross_qty - saleable_qty
		material_cost = material_map.get(d.work_order, 0)
		manpower_cost = flt(saleable_qty) * flt(d.manpower_rate)
		utilities_cost = flt(saleable_qty) * flt(d.utilities_rate)
		total_cost = material_cost + manpower_cost + utilities_cost
		selling_price = price_map.get(d.item_code, 0)
		sales_value = flt(saleable_qty) * selling_price
		profit = sales_value - total_cost

		data.append({
			"work_order": d.work_order,
			"posting_date": d.actual_end_date,
			"item_code": d.item_code,
			"item_name": d.item_name,
			"status": d.status,
			"gross_qty": gross_qty,
			"saleable_qty": saleable_qty,
			"loss_qty": loss_qty,
			"loss_pct": (loss_qty / gross_qty * 100) if gross_qty else 0,
			"material_cost": material_cost,
			"manpower_rate": flt(d.manpower_rate),
			"manpower_cost": manpower_cost,
			"utilities_rate": flt(d.utilities_rate),
			"utilities_cost": utilities_cost,
			"total_cost": total_cost,
			"cost_per_kg": (total_cost / saleable_qty) if saleable_qty else 0,
			"selling_price": selling_price,
			"sales_value": sales_value,
			"profit": profit,
			"profit_pct": (profit / sales_value * 100) if sales_value else 0,
		})

	return data
