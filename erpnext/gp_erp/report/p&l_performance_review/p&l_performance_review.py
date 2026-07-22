# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import calendar

import frappe
from frappe import _
from frappe.utils import (
	add_years,
	cint,
	flt,
	get_first_day,
	get_last_day,
	getdate,
	nowdate,
)

from erpnext.accounts.report.financial_statements import get_data, get_period_list
from erpnext.accounts.utils import get_fiscal_year, remove_account_number
from erpnext.gp_erp.report.budget_variance_greenphyto.budget_variance_greenphyto import (
	add_budget_to_rows,
	add_summary_columns,
	get_budget_account,
	get_budget_data,
	get_net_profit_loss,
)

PAYROLL_ACCOUNT_NUMBER = "600001"

MONTH_NAMES = list(calendar.month_name)


def execute(filters=None):
	filters = control_filters(filters)

	# Monthly view: don't pass month/to_month so get_period_list generates Jan..Dec periods
	# YTD (Yearly): pass month/to_month to get a single Jan-to-to_month period
	month_kw = {}
	if filters.view_mode == "YTD":
		month_kw = {"month": filters.month, "to_month": filters.to_month}

	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.get("filter_based_on"),
		filters.periodicity,
		company=filters.company,
		**month_kw,
	)

	# Limit periods to to_month for Monthly mode
	if filters.view_mode == "Monthly":
		to_m = list(MONTH_NAMES).index(filters.to_month)
		period_list = [p for p in period_list if p.to_date.month <= to_m]

	accounts_list = []
	if cint(filters.hide_zero_balance):
		accounts_list = get_budget_account(filters.get("cost_center"), filters.get("company"))

	income, expense = fetch_pl(filters, period_list, accounts_list)

	budget_map = get_budget_data(filters, ytd=False)
	if income:
		add_budget_to_rows(income, budget_map, period_list, filters)
		add_summary_columns(income, period_list)
	if expense:
		add_budget_to_rows(expense, budget_map, period_list, filters)
		add_summary_columns(expense, period_list)

	merge_prior_year(income, expense, filters, period_list, accounts_list)

	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, filters.company, filters.presentation_currency
	)
	if net_profit_loss:
		apply_prior_to_net(net_profit_loss, income, expense)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss:
		data.append(net_profit_loss)

	append_ratio_rows(data, income, expense, period_list, filters)

	if filters.view_mode == "YTD":
		remap_ytd_fields(data)

	new_data = prepare_display_rows(data, filters)
	columns = get_report_columns(filters, period_list)
	return columns, new_data


def control_filters(filters):
	filters = frappe._dict(filters or {})
	if not filters.get("year"):
		frappe.throw(_("Year is required"))

	filters.view_mode = filters.get("periodicity") or "YTD"
	# get_period_list only knows Monthly/Yearly etc.
	filters.periodicity = "Monthly" if filters.view_mode == "Monthly" else "Yearly"

	filters.month = "January"
	current = getdate(nowdate())
	try:
		year_num = cint(str(filters.year)[:4])
	except Exception:
		year_num = current.year

	if year_num < current.year:
		filters.to_month = "December"
	else:
		filters.to_month = MONTH_NAMES[current.month]

	# Same pattern as budget_variance_greenphyto (Date Range via period_*_date)
	start_date = getdate("{}-01-01".format(year_num))
	end_date = getdate("{}-{}-01".format(year_num, list(MONTH_NAMES).index(filters.to_month)))
	filters.from_fiscal_year = filters.year
	filters.to_fiscal_year = filters.year
	filters.period_start_date = get_first_day(start_date)
	filters.period_end_date = get_last_day(end_date)
	filters.filter_based_on = "Fiscal Year"
	filters.budget_against = filters.get("budget_against") or "Cost Center"
	filters.accumulated_values = cint(filters.get("accumulated_values", 1))
	# Monthly breakdown: net per month
	if filters.view_mode == "Monthly":
		filters.accumulated_values = 0
	return filters


def fetch_pl(filters, period_list, accounts_list=None):
	accounts_list = accounts_list or []
	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
		filter_zero_value=0,
		accounts_to_show=accounts_list,
	)
	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
		filter_zero_value=0,
		accounts_to_show=accounts_list,
	)
	return income, expense


def merge_prior_year(income, expense, filters, period_list, accounts_list):
	try:
		prev_fy = get_fiscal_year(
			add_years(period_list[0].year_start_date, -1),
			company=filters.company,
			as_dict=1,
		)
	except Exception:
		return

	prev_filters = frappe._dict(filters.copy())
	prev_filters.from_fiscal_year = prev_fy.name
	prev_filters.to_fiscal_year = prev_fy.name
	prev_filters.year = prev_fy.name

	prev_month_kw = {}
	if filters.view_mode == "YTD":
		prev_month_kw = {"month": filters.month, "to_month": filters.to_month}
	prev_period_list = get_period_list(
		prev_filters.from_fiscal_year,
		prev_filters.to_fiscal_year,
		None,
		None,
		"Fiscal Year",
		filters.periodicity,
		company=filters.company,
		**prev_month_kw,
	)
	# Limit prior periods too for Monthly mode
	if filters.view_mode == "Monthly":
		to_m = list(MONTH_NAMES).index(filters.to_month)
		prev_period_list = [p for p in prev_period_list if p.to_date.month <= to_m]

	prev_income, prev_expense = fetch_pl(prev_filters, prev_period_list, accounts_list)
	_merge_prior_into(income, prev_income, prev_period_list)
	_merge_prior_into(expense, prev_expense, prev_period_list)


def _merge_prior_into(current_rows, prior_rows, prev_period_list):
	prior_map = {}
	for row in prior_rows or []:
		key = row.get("account_origin") or row.get("account")
		if not key:
			# total / blank rows keyed by account_name
			key = row.get("account_name") or row.get("account")
		if not key:
			continue
		total = sum(flt(row.get(p.key, 0)) for p in prev_period_list)
		# also keep total_actual if already summarized
		if row.get("total_actual") is not None and not prev_period_list:
			total = flt(row.get("total_actual"))
		prior_map[key] = total
		# map total rows by marker
		name = (row.get("account_name") or "").lower()
		if "total" in name and ("income" in name or "expense" in name or "revenue" in name):
			prior_map["__total__" + name] = total

	for row in current_rows or []:
		key = row.get("account_origin") or row.get("account")
		name = (row.get("account_name") or "").lower()
		if "total" in name and ("income" in name or "expense" in name or "revenue" in name):
			prior = flt(prior_map.get("__total__" + name, prior_map.get(key, 0)))
		else:
			prior = flt(prior_map.get(key, 0))
		row["prior_total"] = prior
		actual = flt(row.get("total_actual", 0))
		row["prior_var_amount"] = actual - prior
		row["prior_var_percent"] = flt((row["prior_var_amount"] / prior) * 100, 2) if prior else 0


def apply_prior_to_net(net, income, expense):
	inc = income[-2] if income else {}
	exp = expense[-2] if expense else {}
	net["prior_total"] = flt(inc.get("prior_total", 0)) - flt(exp.get("prior_total", 0))
	net["prior_var_amount"] = flt(net.get("total_actual", 0)) - flt(net["prior_total"])
	prior = flt(net["prior_total"])
	net["prior_var_percent"] = (
		flt((net["prior_var_amount"] / prior) * 100, 2) if prior else 0
	)


def append_ratio_rows(data, income, expense, period_list, filters):
	"""GOP % and Payroll Cost % after Profit/(Loss)."""
	income_total = income[-2] if income else {}
	expense_total = expense[-2] if expense else {}
	currency = (
		filters.get("presentation_currency")
		or frappe.get_cached_value("Company", filters.company, "default_currency")
	)

	revenue = {
		"total_actual": flt(income_total.get("total_actual", 0)),
		"budget_ytd": flt(income_total.get("budget_ytd", 0)),
		"prior_total": flt(income_total.get("prior_total", 0)),
	}
	for period in period_list:
		revenue[period.key] = flt(income_total.get(period.key, 0))
		revenue[period.key + "_budget"] = flt(income_total.get(period.key + "_budget", 0))

	profit = None
	for row in reversed(data):
		if row.get("profit_data"):
			profit = row
			break

	# GOP %
	gop = _blank_ratio_row("GOP %", currency)
	_fill_ratio(gop, profit or {}, revenue, period_list)
	data.append(gop)

	# Payroll Cost %
	payroll_vals = get_payroll_values(filters, period_list)
	payroll_row = _blank_ratio_row("Payroll Cost %", currency)
	_fill_ratio(payroll_row, payroll_vals, revenue, period_list)
	data.append(payroll_row)


def _blank_ratio_row(label, currency):
	return {
		"account_name": label,
		"account": label,
		"is_bold": 1,
		"warn_if_negative": 1,
		"currency": currency,
		"ratio_row": 1,
	}


def _fill_ratio(target, numerator_row, revenue, period_list):
	"""ratio = numerator / revenue for each summary + period key."""
	for field in ("total_actual", "budget_ytd", "prior_total"):
		num = flt((numerator_row or {}).get(field, 0))
		den = flt(revenue.get(field, 0))
		target[field] = flt((num / den) * 100, 2) if den else 0

	target["variance_amount"] = flt(target.get("total_actual", 0)) - flt(target.get("budget_ytd", 0))
	bud = flt(target.get("budget_ytd", 0))
	target["variance_percent"] = (
		flt((target["variance_amount"] / bud) * 100, 2) if bud else 0
	)
	target["prior_var_amount"] = flt(target.get("total_actual", 0)) - flt(target.get("prior_total", 0))
	prior = flt(target.get("prior_total", 0))
	target["prior_var_percent"] = (
		flt((target["prior_var_amount"] / prior) * 100, 2) if prior else 0
	)

	for period in period_list:
		num = flt((numerator_row or {}).get(period.key, 0))
		den = flt(revenue.get(period.key, 0))
		target[period.key] = flt((num / den) * 100, 2) if den else 0
		num_b = flt((numerator_row or {}).get(period.key + "_budget", 0))
		den_b = flt(revenue.get(period.key + "_budget", 0))
		target[period.key + "_budget"] = flt((num_b / den_b) * 100, 2) if den_b else 0


def get_payroll_values(filters, period_list):
	"""SUM GL of account_number 600001 descendants, shaped like a row with period keys + totals."""
	account = frappe.db.get_value(
		"Account",
		{"account_number": PAYROLL_ACCOUNT_NUMBER, "company": filters.company},
		["name", "lft", "rgt", "is_group"],
		as_dict=1,
	)
	if not account:
		# fallback any company with that number (spec: resolve by company filter first)
		account = frappe.db.get_value(
			"Account",
			{"account_number": PAYROLL_ACCOUNT_NUMBER},
			["name", "lft", "rgt", "is_group", "company"],
			as_dict=1,
		)
	if not account:
		return {}

	leaf_accounts = frappe.db.sql(
		"""
		select name from `tabAccount`
		where lft >= %s and rgt <= %s and ifnull(is_group, 0) = 0 and company = %s
		""",
		(account.lft, account.rgt, filters.company if "company" not in account else account.get("company") or filters.company),
		pluck="name",
	)
	if not leaf_accounts and not account.is_group:
		leaf_accounts = [account.name]
	if not leaf_accounts:
		return {}

	company = filters.company
	conditions = ["gle.company = %(company)s", "gle.is_cancelled = 0", "gle.account in %(accounts)s"]
	values = {
		"company": company,
		"accounts": leaf_accounts,
		"from_date": period_list[0].from_date,
		"to_date": period_list[-1].to_date,
	}

	if filters.get("cost_center"):
		from erpnext.accounts.report.financial_statements import get_cost_centers_with_children

		ccs = get_cost_centers_with_children(filters.cost_center)
		conditions.append("gle.cost_center in %(cost_center)s")
		values["cost_center"] = ccs

	conditions.append("gle.posting_date between %(from_date)s and %(to_date)s")

	rows = frappe.db.sql(
		"""
		select gle.posting_date, sum(gle.debit) - sum(gle.credit) as balance
		from `tabGL Entry` gle
		where {cond}
		group by gle.posting_date
		""".format(cond=" and ".join(conditions)),
		values,
		as_dict=1,
	)

	result = {p.key: 0.0 for p in period_list}
	result["total_actual"] = 0.0
	for r in rows:
		posting = getdate(r.posting_date)
		bal = flt(r.balance)
		for p in period_list:
			if p.from_date <= posting <= p.to_date:
				if filters.accumulated_values:
					# accumulated: all postings up to period.to_date within year range
					pass
				result[p.key] = flt(result.get(p.key, 0)) + bal
				break
		result["total_actual"] = flt(result["total_actual"]) + bal

	if filters.accumulated_values and filters.periodicity == "Monthly":
		running = 0.0
		for p in period_list:
			running += flt(result.get(p.key, 0))
			result[p.key] = running

	# budget for payroll group: sum descendants from budget_map already on expense tree if present
	# compute from get_budget_data
	budget_map = get_budget_data(filters, ytd=False)
	start_m = list(MONTH_NAMES).index(filters.month) if filters.month in MONTH_NAMES else 1
	end_m = list(MONTH_NAMES).index(filters.to_month) if filters.to_month in MONTH_NAMES else 12

	budget_ytd = 0.0
	# sum budget for all leaf accounts under payroll
	for acc in leaf_accounts:
		for m in range(start_m, end_m + 1):
			budget_ytd += flt(budget_map.get(acc, {}).get(m, 0))
	# also try group account key
	for m in range(start_m, end_m + 1):
		budget_ytd += flt(budget_map.get(account.name, {}).get(m, 0))

	result["budget_ytd"] = budget_ytd

	# prior year payroll
	try:
		prev_fy = get_fiscal_year(
			add_years(period_list[0].year_start_date, -1),
			company=filters.company,
			as_dict=1,
		)
		prev_from = add_years(period_list[0].from_date, -1)
		prev_to = add_years(period_list[-1].to_date, -1)
		prev_values = dict(values)
		prev_values["from_date"] = prev_from
		prev_values["to_date"] = prev_to
		prev_values["company"] = company
		prev_total = frappe.db.sql(
			"""
			select coalesce(sum(gle.debit) - sum(gle.credit), 0)
			from `tabGL Entry` gle
			where {cond}
			""".format(cond=" and ".join(conditions)),
			prev_values,
		)[0][0]
		result["prior_total"] = flt(prev_total)
	except Exception:
		result["prior_total"] = 0

	return result


def remap_ytd_fields(data):
	"""YTD view: expose ytd_* fieldnames from summary fields."""
	mapping = {
		"total_actual": "ytd_actual",
		"budget_ytd": "ytd_budget",
		"variance_amount": "ytd_var_amount",
		"variance_percent": "ytd_var_percent",
		"prior_total": "ytd_prior_actual",
		"prior_var_amount": "ytd_py_var_amount",
		"prior_var_percent": "ytd_py_var_percent",
	}
	for row in data:
		if not row:
			continue
		for src, dst in mapping.items():
			if src in row:
				row[dst] = row[src]


def prepare_display_rows(data, filters):
	new_data = []
	for d in data:
		if not d:
			new_data.append(d)
			continue
		if d.get("is_group") and not filters.get("show_number_group"):
			d["account_name"] = remove_account_number(d.get("account_name") or "")
			if frappe.flags.in_export:
				d["account"] = d["account_name"]
		# rename total labels closer to template
		name = d.get("account_name") or ""
		if "Total Income" in name:
			d["account_name"] = "Total Revenue"
			d["account"] = "Total Revenue"
		elif "Total Expense" in name:
			d["account_name"] = "Total Expenses"
			d["account"] = "Total Expenses"
		if d.get("profit_data"):
			if filters.get("periodicity") == "Monthly":
				d["account_name"] = "Profit/(Loss) for the Month"
			else:
				d["account_name"] = "Profit/(Loss) for the Year"
			d["account"] = "Profit/(Loss)"
		new_data.append(d)
	return new_data


def get_report_columns(filters, period_list):
	currency = filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	columns = [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		},
		{
			"fieldname": "acc_code",
			"label": _("Acc. Code"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]

	# Short year labels: filters.year = "2026" → cur="26", prev="25"
	year_str = str(filters.year)[-2:]
	prev_year_str = str(cint(filters.year) - 1)[-2:]

	if filters.view_mode == "Monthly":
		for period in period_list:
			columns.append(
				{
					"fieldname": period.key,
					"label": period.label,
					"fieldtype": "Currency",
					"options": "currency",
					"width": 130,
				}
			)
			# Budget column per period (same pattern as financial_statements.py)
			budget_key = period.key + "_budget"
			month_label = period.label.split()[0] if period.label else ""
			columns.append(
				{
					"fieldname": budget_key,
					"label": _("{0} Budget").format(month_label),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 130,
				}
			)
		columns.extend(
			[
				_cur("total_actual", _("Total Actual")),
				_cur("budget_ytd", _("Budget YTD")),
				_cur("variance_amount", _("Variance ($)"), width=0, hidden=1),
				_pct("variance_percent", _("Variance (%)"), width=0, hidden=1),
				_cur("prior_total", _("Act'{0}").format(prev_year_str)),
				_cur(
					"prior_var_amount",
					_("Act'{0} vs Act'{1} ($)").format(year_str, prev_year_str),
					width=170,
				),
				_pct(
					"prior_var_percent",
					_("Act'{0} vs Act'{1} (%)").format(year_str, prev_year_str),
					width=170,
				),
			]
		)
	else:
		columns.extend(
			[
				_cur("ytd_actual", _("Actual YTD")),
				_cur("ytd_budget", _("Budget YTD")),
				_cur("ytd_var_amount", _("Act vs Budget ($)"), width=0, hidden=1),
				_pct("ytd_var_percent", _("Act vs Budget (%)"), width=0, hidden=1),
				_cur(
					"ytd_prior_actual",
					_("Act'{0}").format(prev_year_str),
				),
				_cur(
					"ytd_py_var_amount",
					_("Act'{0} vs Act'{1} ($)").format(year_str, prev_year_str),
					width=170,
				),
				_pct(
					"ytd_py_var_percent",
					_("Act'{0} vs Act'{1} (%)").format(year_str, prev_year_str),
					width=170,
				),
			]
		)

	return columns


def _cur(fieldname, label, width=140, hidden=0):
	col = {
		"fieldname": fieldname,
		"label": label,
		"fieldtype": "Currency",
		"options": "currency",
		"width": width,
	}
	if hidden:
		col["hidden"] = 1
	return col


def _pct(fieldname, label, width=120, hidden=0):
	col = {
		"fieldname": fieldname,
		"label": label,
		"fieldtype": "Percent",
		"width": width,
	}
	if hidden:
		col["hidden"] = 1
	return col
