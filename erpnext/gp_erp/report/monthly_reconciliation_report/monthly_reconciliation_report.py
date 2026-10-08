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
		{
			"fieldname": "period",
			"label": _("Period"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "cost_component",
			"label": _("Cost Component"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "expense_account",
			"label": _("Expense Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 220,
		},
		{
			"fieldname": "wo_qty",
			"label": _("Work Order Qty (kg)"),
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"fieldname": "rate_per_kg",
			"label": _("Rate per kg"),
			"fieldtype": "Currency",
			"width": 110,
		},
		{
			"fieldname": "actual_expense",
			"label": _("Actual Expense (GL Dr)"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "absorbed_cost",
			"label": _("Absorbed to Work Orders"),
			"fieldtype": "Currency",
			"width": 160,
		},
		{
			"fieldname": "variance",
			"label": _("Variance (Under)/Over Absorbed"),
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"fieldname": "absorption_pct",
			"label": _("Absorption %"),
			"fieldtype": "Percent",
			"width": 120,
		},
	]


def get_component_account_map(company):
	# expense account per cost component, from Rate Card account settings
	rows = frappe.get_all(
		"Rate Card",
		filters={"company": company},
		fields=["expense_for_manpower", "expense_for_electricity"],
	)

	accounts = {}
	for d in rows:
		if d.expense_for_manpower:
			accounts.setdefault("Manpower", d.expense_for_manpower)
		if d.expense_for_electricity:
			accounts.setdefault("Utilities", d.expense_for_electricity)

	if not accounts:
		default_account = frappe.db.get_value("Company", company, "default_cost_expense_account")
		if default_account:
			accounts["Production Cost"] = default_account

	return accounts


def get_wo_absorption(filters):
	# absorbed cost per period per component: produced qty (kg) x rate card rate
	# rate card is linked per production item (Item.rate_card),
	# component rates come from Rate Card Detail (Harvesting operation)
	rows = frappe.db.sql(
		"""
		SELECT
			DATE_FORMAT(wo.actual_end_date, '%%Y-%%m') AS period,
			SUM(wo.produced_qty) AS produced_qty,
			SUM(wo.produced_qty * rcd.manpower) AS manpower_amount,
			SUM(wo.produced_qty * rcd.electricity) AS utilities_amount
		FROM `tabWork Order` wo
			INNER JOIN `tabItem` i ON i.name = wo.production_item
			INNER JOIN `tabRate Card` rc ON rc.name = i.rate_card
			INNER JOIN `tabRate Card Detail` rcd ON rcd.parent = rc.name
				AND rcd.operation = 'Harvesting'
		WHERE
			wo.docstatus = 1
			AND wo.company = %(company)s
			AND wo.status IN ('Completed', 'Stopped')
			AND wo.actual_end_date BETWEEN %(from_date)s AND %(to_date)s
			AND i.rate_card IS NOT NULL
		GROUP BY period
		""",
		{
			"company": filters.company,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
		},
		as_dict=1,
	)

	absorbed = frappe._dict()
	for d in rows:
		absorbed[(d.period, "Manpower")] = {
			"qty": flt(d.produced_qty),
			"amount": flt(d.manpower_amount),
		}
		absorbed[(d.period, "Utilities")] = {
			"qty": flt(d.produced_qty),
			"amount": flt(d.utilities_amount),
		}

	return absorbed


def get_data(filters):
	company = filters.company or frappe.defaults.get_user_default("Company")

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if not (from_date and to_date):
		from_date = to_date = frappe.utils.today()

	accounts = get_component_account_map(company)
	if not accounts:
		return []

	gl = frappe.db.sql(
		"""
		SELECT
			DATE_FORMAT(posting_date, '%%Y-%%m') AS period,
			account,
			SUM(debit_in_account_currency) AS debit
		FROM `tabGL Entry`
		WHERE
			company = %(company)s
			AND posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND account IN %(accounts)s
			AND is_cancelled = 0
		GROUP BY period, account
		""",
		{
			"company": company,
			"from_date": from_date,
			"to_date": to_date,
			"accounts": list(accounts.values()),
		},
		as_dict=1,
	)

	actual = {(d.period, d.account): flt(d.debit) for d in gl}
	absorbed = get_wo_absorption(frappe._dict({
		"company": company,
		"from_date": from_date,
		"to_date": to_date,
	}))

	# union of periods from GL and work orders
	periods = set()
	for period_key, _account in actual:
		periods.add(period_key)
	for period_key, _component in absorbed:
		periods.add(period_key)

	account_by_component = {c: a for a, c in accounts.items()}
	data = []
	for period in sorted(periods):
		for component in ("Manpower", "Utilities", "Production Cost"):
			account = account_by_component.get(component)
			abs = absorbed.get((period, component), {})
			actual_amount = actual.get((period, account), 0) if account else 0
			absorbed_amount = flt(abs.get("amount"))
			if not actual_amount and not absorbed_amount:
				continue

			wo_qty = flt(abs.get("qty"))
			variance = actual_amount - absorbed_amount
			data.append({
				"period": period,
				"cost_component": component,
				"expense_account": account,
				"wo_qty": wo_qty,
				"rate_per_kg": (absorbed_amount / wo_qty) if wo_qty else 0,
				"actual_expense": actual_amount,
				"absorbed_cost": absorbed_amount,
				"variance": variance,
				"absorption_pct": (absorbed_amount / actual_amount * 100) if actual_amount else 0,
			})

	return data
