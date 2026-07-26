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

	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.get("filter_based_on"),
		filters.periodicity,
		company=filters.company,
	)

	# Limit periods to to_month; display only selected month as a column
	to_m = list(MONTH_NAMES).index(filters.to_month)
	period_list = [p for p in period_list if p.to_date.month <= to_m]
	display_period_list = period_list[-1:]

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

	# Monthly act-vs-budget for displayed month (always net-for-that-month)
	_month_key = display_period_list[-1].key
	for _rows in (income, expense):
		fill_monthly_variance(_rows, _month_key)

	merge_prior_year(income, expense, filters, period_list, accounts_list, _month_key)

	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, filters.company, filters.presentation_currency
	)
	if net_profit_loss:
		fill_monthly_variance([net_profit_loss], _month_key)
		apply_prior_to_net(net_profit_loss, income, expense)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss:
		data.append(net_profit_loss)

	append_ratio_rows(data, income, expense, period_list, filters, _month_key)

	new_data = prepare_display_rows(data, filters)
	columns = get_report_columns(filters, display_period_list)
	return columns, new_data


def control_filters(filters):
	filters = frappe._dict(filters or {})
	if not filters.get("year"):
		frappe.throw(_("Year is required"))

	# Always monthly system — no YTD / Accumulated toggle
	filters.view_mode = "Monthly"
	filters.periodicity = "Monthly"
	filters.accumulated_values = 0
	filters.display_accumulated = 0

	filters.month = "January"
	current = getdate(nowdate())
	try:
		year_num = cint(str(filters.year)[:4])
	except Exception:
		year_num = current.year

	if filters.get("to_month") in MONTH_NAMES:
		pass
	elif year_num < current.year:
		filters.to_month = "December"
	else:
		filters.to_month = MONTH_NAMES[current.month]

	start_date = getdate("{}-01-01".format(year_num))
	end_date = getdate("{}-{}-01".format(year_num, list(MONTH_NAMES).index(filters.to_month)))
	filters.from_fiscal_year = filters.year
	filters.to_fiscal_year = filters.year
	filters.period_start_date = get_first_day(start_date)
	filters.period_end_date = get_last_day(end_date)
	filters.filter_based_on = "Fiscal Year"
	filters.budget_against = filters.get("budget_against") or "Cost Center"
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


def fill_monthly_variance(rows, month_key):
	"""Act vs Budget for the single displayed month."""
	budget_key = month_key + "_budget"
	for row in rows or []:
		if not row:
			continue
		act = flt(row.get(month_key, 0))
		bud = flt(row.get(budget_key, 0))
		row["monthly_var_amount"] = act - bud
		row["monthly_var_percent"] = flt((row["monthly_var_amount"] / bud) * 100, 2) if bud else 0


def merge_prior_year(income, expense, filters, period_list, accounts_list, month_key):
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

	prev_period_list = get_period_list(
		prev_filters.from_fiscal_year,
		prev_filters.to_fiscal_year,
		None,
		None,
		"Fiscal Year",
		filters.periodicity,
		company=filters.company,
	)
	to_m = list(MONTH_NAMES).index(filters.to_month)
	prev_period_list = [p for p in prev_period_list if p.to_date.month <= to_m]

	prev_income, prev_expense = fetch_pl(prev_filters, prev_period_list, accounts_list)
	_merge_prior_into(income, prev_income, prev_period_list)
	_merge_prior_into(expense, prev_expense, prev_period_list)


def _merge_prior_into(current_rows, prior_rows, prev_period_list):
	prior_map = {}
	prior_month_map = {}
	last_key = prev_period_list[-1].key if prev_period_list else None

	for row in prior_rows or []:
		key = row.get("account_origin") or row.get("account")
		if not key:
			key = row.get("account_name") or row.get("account")
		if not key:
			continue
		total = sum(flt(row.get(p.key, 0)) for p in prev_period_list)
		month_val = flt(row.get(last_key, 0)) if last_key else 0
		prior_map[key] = total
		prior_month_map[key] = month_val
		name = (row.get("account_name") or "").lower()
		if "total" in name and ("income" in name or "expense" in name or "revenue" in name):
			prior_map["__total__" + name] = total
			prior_month_map["__total__" + name] = month_val

	for row in current_rows or []:
		key = row.get("account_origin") or row.get("account")
		name = (row.get("account_name") or "").lower()
		if "total" in name and ("income" in name or "expense" in name or "revenue" in name):
			prior = flt(prior_map.get("__total__" + name, prior_map.get(key, 0)))
			prior_m = flt(prior_month_map.get("__total__" + name, prior_month_map.get(key, 0)))
		else:
			prior = flt(prior_map.get(key, 0))
			prior_m = flt(prior_month_map.get(key, 0))

		# YTD prior
		row["prior_total"] = prior
		actual_ytd = flt(row.get("total_actual", 0))
		row["prior_var_amount"] = actual_ytd - prior
		row["prior_var_percent"] = flt((row["prior_var_amount"] / prior) * 100, 2) if prior else 0

		# Monthly prior (same month last year)
		row["prior_month"] = prior_m
		# month actual is already on row under period key; var filled later if needed
		# Use displayed month from total path: caller sets via fill after knowing month_key
		# Store prior_month only; monthly prior var computed in fill_prior_month_var


def fill_prior_month_var(rows, month_key):
	for row in rows or []:
		if not row:
			continue
		act = flt(row.get(month_key, 0))
		prior_m = flt(row.get("prior_month", 0))
		row["prior_month_var_amount"] = act - prior_m
		row["prior_month_var_percent"] = (
			flt((row["prior_month_var_amount"] / prior_m) * 100, 2) if prior_m else 0
		)


def apply_prior_to_net(net, income, expense):
	inc = income[-2] if income else {}
	exp = expense[-2] if expense else {}
	net["prior_total"] = flt(inc.get("prior_total", 0)) - flt(exp.get("prior_total", 0))
	net["prior_var_amount"] = flt(net.get("total_actual", 0)) - flt(net["prior_total"])
	prior = flt(net["prior_total"])
	net["prior_var_percent"] = (
		flt((net["prior_var_amount"] / prior) * 100, 2) if prior else 0
	)
	net["prior_month"] = flt(inc.get("prior_month", 0)) - flt(exp.get("prior_month", 0))
	# prior_month_var filled by fill_prior_month_var after net is built


def append_ratio_rows(data, income, expense, period_list, filters, month_key):
	"""GOP % and Payroll Cost % after Profit/(Loss)."""
	income_total = income[-2] if income else {}
	currency = (
		filters.get("presentation_currency")
		or frappe.get_cached_value("Company", filters.company, "default_currency")
	)

	revenue = {
		"total_actual": flt(income_total.get("total_actual", 0)),
		"budget_ytd": flt(income_total.get("budget_ytd", 0)),
		"prior_total": flt(income_total.get("prior_total", 0)),
		"prior_month": flt(income_total.get("prior_month", 0)),
	}
	for period in period_list:
		revenue[period.key] = flt(income_total.get(period.key, 0))
		revenue[period.key + "_budget"] = flt(income_total.get(period.key + "_budget", 0))

	profit = None
	for row in reversed(data):
		if row.get("profit_data"):
			profit = row
			break

	gop = _blank_ratio_row("GOP %", currency)
	_fill_ratio(gop, profit or {}, revenue, period_list, month_key)
	data.append(gop)

	payroll_vals = get_payroll_values(filters, period_list)
	payroll_row = _blank_ratio_row("Payroll Cost %", currency)
	_fill_ratio(payroll_row, payroll_vals, revenue, period_list, month_key)
	data.append(payroll_row)

	# prior_month_var for all data rows that have prior_month
	for row in data:
		if row and "prior_month" in row:
			fill_prior_month_var([row], month_key)


def _blank_ratio_row(label, currency):
	return {
		"account_name": label,
		"account": label,
		"is_bold": 1,
		"warn_if_negative": 1,
		"currency": currency,
		"ratio_row": 1,
	}


def _fill_ratio(target, numerator_row, revenue, period_list, month_key):
	"""ratio = numerator / revenue for each summary + period key."""
	for field in ("total_actual", "budget_ytd", "prior_total", "prior_month"):
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

	# Monthly act-vs-budget %
	act_m = flt(target.get(month_key, 0))
	bud_m = flt(target.get(month_key + "_budget", 0))
	target["monthly_var_amount"] = act_m - bud_m
	target["monthly_var_percent"] = flt((target["monthly_var_amount"] / bud_m) * 100, 2) if bud_m else 0


def get_payroll_values(filters, period_list):
	"""SUM GL of account_number 600001 descendants, shaped like a row with period keys + totals."""
	account = frappe.db.get_value(
		"Account",
		{"account_number": PAYROLL_ACCOUNT_NUMBER, "company": filters.company},
		["name", "lft", "rgt", "is_group"],
		as_dict=1,
	)
	if not account:
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
				result[p.key] = flt(result.get(p.key, 0)) + bal
				break
		result["total_actual"] = flt(result["total_actual"]) + bal

	budget_map = get_budget_data(filters, ytd=False)
	start_m = list(MONTH_NAMES).index(filters.month) if filters.month in MONTH_NAMES else 1
	end_m = list(MONTH_NAMES).index(filters.to_month) if filters.to_month in MONTH_NAMES else 12

	for p in period_list:
		p_to_date = getdate(p.to_date) if p.to_date else None
		budget_key = p.key + "_budget"
		budget_value = 0.0
		if p_to_date:
			month_num = p_to_date.month
			budget_value = sum(flt(budget_map.get(acc, {}).get(month_num, 0)) for acc in leaf_accounts)
		result[budget_key] = budget_value

	budget_ytd = 0.0
	for acc in leaf_accounts:
		for m in range(start_m, end_m + 1):
			budget_ytd += flt(budget_map.get(acc, {}).get(m, 0))
	for m in range(start_m, end_m + 1):
		budget_ytd += flt(budget_map.get(account.name, {}).get(m, 0))
	result["budget_ytd"] = budget_ytd

	# prior year payroll: YTD + single month
	try:
		prev_from = add_years(period_list[0].from_date, -1)
		prev_to = add_years(period_list[-1].to_date, -1)
		prev_month_from = add_years(period_list[-1].from_date, -1)
		prev_month_to = add_years(period_list[-1].to_date, -1)

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

		prev_m_values = dict(values)
		prev_m_values["from_date"] = prev_month_from
		prev_m_values["to_date"] = prev_month_to
		prev_m_values["company"] = company
		prev_month = frappe.db.sql(
			"""
			select coalesce(sum(gle.debit) - sum(gle.credit), 0)
			from `tabGL Entry` gle
			where {cond}
			""".format(cond=" and ".join(conditions)),
			prev_m_values,
		)[0][0]
		result["prior_month"] = flt(prev_month)
	except Exception:
		result["prior_total"] = 0
		result["prior_month"] = 0

	return result


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
		name = d.get("account_name") or ""
		if "Total Income" in name:
			d["account_name"] = "Total Revenue"
			d["account"] = "Total Revenue"
		elif "Total Expense" in name:
			d["account_name"] = "Total Expenses"
			d["account"] = "Total Expenses"
		if d.get("profit_data"):
			d["account_name"] = "Profit/(Loss)"
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
	]

	year_str = str(filters.year)[-2:]
	prev_year_str = str(cint(filters.year) - 1)[-2:]
	month_abbr = (filters.to_month or "")[:3]

	for period in period_list:
		# Act May 26
		columns.append(
			{
				"fieldname": period.key,
				"label": _("Act {0} '{1}").format(month_abbr, year_str),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			}
		)
		# Budget May 26
		columns.append(
			{
				"fieldname": period.key + "_budget",
				"label": _("Budget {0} '{1}").format(month_abbr, year_str),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 130,
			}
		)

	columns.extend(
		[
			_cur("monthly_var_amount", _("Act vs Budget (Month) ($)"), width=200),
			_pct("monthly_var_percent", _("Act vs Budget (Month) (%)"), width=200),
			_cur("prior_month", _("Act {0} '{1}").format(month_abbr, prev_year_str)),
			_cur(
				"prior_month_var_amount",
				_("Act {0} '{1} vs Act {0} '{2} ($)").format(month_abbr, year_str, prev_year_str),
				width=230,
			),
			_pct(
				"prior_month_var_percent",
				_("Act {0} '{1} vs Act {0} '{2} (%)").format(month_abbr, year_str, prev_year_str),
				width=230,
			),
			_cur("total_actual", _("Actual YTD"), width=140),
			_cur("budget_ytd", _("Budget YTD"), width=140),
			_cur("variance_amount", _("Act vs Budget Yearly ($)"), width=200),
			_pct("variance_percent", _("Act vs Budget Yearly (%)"), width=200),
			_cur("prior_total", _("Act '{0}").format(prev_year_str)),
			_cur(
				"prior_var_amount",
				_("Act YTD '{0} vs Act YTD '{1} ($)").format(year_str, prev_year_str),
				width=230,
			),
			_pct(
				"prior_var_percent",
				_("Act YTD '{0} vs Act YTD '{1} (%)").format(year_str, prev_year_str),
				width=230,
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


def add_borders(report_name, xlsx_file):
	import re
	from io import BytesIO

	from openpyxl import load_workbook
	from openpyxl.styles import Border, Side

	stream = BytesIO(xlsx_file.getvalue())
	wb = load_workbook(stream)
	thick = Side(style="thick")

	# Each box: (start pattern for first column, end pattern for last column)
	boxes = [
		(re.compile(r"^Act .+'\d+$"), re.compile(r"vs Act .+\(%\)$")),
		(re.compile(r"^Actual YTD$"), re.compile(r"vs Act YTD .+\(%\)$")),
	]

	def find_box(ws, start_re, end_re):
		header_row = min_col = max_col = None
		for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
			for cell in row:
				if not isinstance(cell.value, str):
					continue
				if min_col is None and start_re.match(cell.value):
					header_row = cell.row
					min_col = cell.column
				elif min_col is not None and max_col is None and end_re.search(cell.value):
					max_col = cell.column
			if header_row and min_col and max_col:
				break
		return header_row, min_col, max_col

	def find_last_row(ws, header_row, label="Payroll Cost %"):
		for row in ws.iter_rows(min_row=header_row, max_row=ws.max_row, min_col=1, max_col=1):
			if row[0].value == label:
				return row[0].row
		return ws.max_row

	for ws in wb.worksheets:
		for start_re, end_re in boxes:
			header_row, min_col, max_col = find_box(ws, start_re, end_re)
			if not (header_row and min_col and max_col):
				continue

			max_row = find_last_row(ws, header_row)

			for row_idx in range(header_row, max_row + 1):
				for col_idx in range(min_col, max_col + 1):
					cell = ws.cell(row=row_idx, column=col_idx)
					cell.border = Border(
						top=thick if row_idx == header_row else cell.border.top,
						bottom=thick if row_idx == max_row else cell.border.bottom,
						left=thick if col_idx == min_col else cell.border.left,
						right=thick if col_idx == max_col else cell.border.right,
					)

	output_stream = BytesIO()
	wb.save(output_stream)
	output_stream.seek(0)

	from frappe.utils import get_datetime, now

	date_str_title = " " + get_datetime(now()).strftime("%y%m%d%H%M%S")
	frappe.response["filename"] = report_name + date_str_title + ".xlsx"
	frappe.response["filecontent"] = output_stream.getvalue()
	frappe.response["type"] = "binary"
