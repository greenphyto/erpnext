import frappe
from frappe import _
from frappe.utils import flt, get_first_day, get_last_day, getdate


def execute(filters=None):
	filters = control_filters(filters)
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def control_filters(filters):
	if not filters:
		filters = frappe._dict()

	year = filters.get("year")
	month = filters.get("month")
	to_month = filters.get("to_month")

	if year:
		filters.from_fiscal_year = year
		filters.to_fiscal_year = year

	if year and month:
		date_str = f"{year}-{month}-01"
		filters.period_start_date = get_first_day(date_str)

	if year and to_month:
		to_date_str = f"{year}-{to_month}-01"
		filters.period_end_date = get_last_day(to_date_str)

	return filters


def get_columns(filters):
	return [
		{"fieldname": "account", "label": _("Account"), "fieldtype": "Link", "options": "Account", "width": 300},
		{"fieldname": "total_actual", "label": _("Total Actual"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "budget_ytd", "label": _("Budget YTD"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "variance_amount", "label": _("Variance"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "variance_percent", "label": _("Variance %"), "fieldtype": "Percent", "width": 100},
	]


def get_data(filters):
	budget_accounts = get_budget_account(
		cost_center=filters.get("cost_center"),
		company=filters.get("company"),
	)
	budget_data = get_budget_data(filters)
	return budget_accounts


def get_budget_account(cost_center=None, company=None):
	conditions = {"company": company} if company else {}

	if cost_center:
		budgets = frappe.db.get_all("Budget", filters={
			"docstatus": 1,
			"cost_center": ["in", cost_center],
			**conditions,
		}, pluck="name")
	else:
		budgets = frappe.db.get_all("Budget", filters={
			"docstatus": 1,
			**conditions,
		}, pluck="name")

	accounts = []
	for budget in budgets:
		items = frappe.db.get_all("Budget Account", filters={"parent": budget}, fields=["account", "budget_amount"])
		for item in items:
			accounts.append(item)

	return accounts


def get_budget_data(filters):
	data = {}

	company = filters.get("company")
	from_fiscal_year = filters.get("from_fiscal_year")
	to_fiscal_year = filters.get("to_fiscal_year")
	budget_against = filters.get("budget_against", "Cost Center")

	if not company or not from_fiscal_year:
		return data

	fy_filters = {"docstatus": 1, "company": company}
	if from_fiscal_year and to_fiscal_year and from_fiscal_year != to_fiscal_year:
		fiscal_years = frappe.db.get_all("Fiscal Year",
			filters={"name": [">=", from_fiscal_year]},
			pluck="name"
		)
		fiscal_years = [fy for fy in fiscal_years if fy <= to_fiscal_year]
		if not fiscal_years:
			fiscal_years = [from_fiscal_year]
		fy_filters["fiscal_year"] = ["in", fiscal_years]
	else:
		fy_filters["fiscal_year"] = from_fiscal_year

	budgets = frappe.db.get_all("Budget", filters=fy_filters,
		fields=["name", "cost_center", "fiscal_year"])

	for budget in budgets:
		items = frappe.db.get_all("Budget Account", filters={"parent": budget.name}, fields=["account", "budget_amount"])
		for item in items:
			key = (budget.cost_center, item.account)
			if key not in data:
				data[key] = {"budget_amount": 0}
			data[key]["budget_amount"] += flt(item.budget_amount)

	return data


def add_summary_columns(rows, period_list):
	for row in rows:
		if row.get("profit_data"):
			continue

		total_actual = 0
		budget_ytd = 0

		for period in period_list:
			key = period.get("key")
			total_actual += flt(row.get(key, 0))
			budget_ytd += flt(row.get(f"{key}_budget", 0))

		row["total_actual"] = total_actual
		row["budget_ytd"] = budget_ytd
		row["variance_amount"] = total_actual - budget_ytd

		if budget_ytd:
			row["variance_percent"] = flt((total_actual - budget_ytd) / budget_ytd * 100, 1)
		else:
			row["variance_percent"] = 0
