# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
import re
import json
from urllib.parse import quote
from io import BytesIO
try:
	import openpyxl
except Exception:
	openpyxl = None
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, now

from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)
from erpnext.accounts.utils import remove_account_number
from erpnext.accounts.report.utils import convert_wrap_report_data


def execute(filters=None):
	filters = frappe._dict(filters)
	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
		month=filters.month,
		to_month=filters.to_month,
	)

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
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
	)

	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, filters.company, filters.presentation_currency
	)

	data = []
	data.extend(income or [])
	data.extend(expense or [])
	if net_profit_loss:
		data.append(net_profit_loss)

	new_data = []
	if filters.show_number_group:
		new_data = data
	else:
		for d in data:
			if d.get("is_group"):
				d['account_name'] = remove_account_number(d['account_name'])
				if frappe.flags.in_export:
					d['account'] = d['account_name']
					if not d.get('parent_account'):
						for key, val in d.items():
							if key not in ['account', 'account_name']:
								d[key] = None

			new_data.append(d)

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, filters.company, cost_center_all_show=filters.show_all_cost_centers, filters=filters
	)

	chart = get_chart_data(filters, columns, income, expense, net_profit_loss)

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	report_summary = get_report_summary(
		period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
	)

	# if frappe.flags.in_export:
	# 	convert_wrap_report_data(columns, data, precision=2)

	return columns, data, None, chart, report_summary


def get_report_summary(
	period_list, periodicity, income, expense, net_profit_loss, currency, filters, consolidated=False
):
	net_income, net_expense, net_profit = 0.0, 0.0, 0.0

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	for period in period_list:
		key = period if consolidated else period.key
		if income:
			net_income += income[-2].get(key)
		if expense:
			net_expense += expense[-2].get(key)
		if net_profit_loss:
			net_profit += net_profit_loss.get(key)

	if len(period_list) == 1 and periodicity == "Yearly":
		profit_label = _("Profit This Year")
		income_label = _("Total Income This Year")
		expense_label = _("Total Expense This Year")
	else:
		profit_label = _("Net Profit")
		income_label = _("Total Income")
		expense_label = _("Total Expense")

	return [
		{"value": net_income, "label": income_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "-"},
		{"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"value": net_profit,
			"indicator": "Green" if net_profit > 0 else "Red",
			"label": profit_label,
			"datatype": "Currency",
			"currency": currency,
		},
	]


def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False):
	total = 0
	net_profit_loss = {
		"account_name": "'" + _("Profit for the year") + "'",
		"account": "'" + _("Profit for the year") + "'",
		"warn_if_negative": True,
		"profit_data":1,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income[-2][key], 3) if income else 0
		total_expense = flt(expense[-2][key], 3) if expense else 0

		net_profit_loss[key] = total_income - total_expense

		if net_profit_loss[key]:
			has_value = True

		total += flt(net_profit_loss[key])
		net_profit_loss["total"] = total

	if has_value:
		return net_profit_loss


def get_chart_data(filters, columns, income, expense, net_profit_loss):
	labels = [d.get("label") for d in columns[2:]]

	income_data, expense_data, net_profit = [], [], []

	for p in columns[2:]:
		if income:
			income_data.append(income[-2].get(p.get("fieldname")))
		if expense:
			expense_data.append(expense[-2].get(p.get("fieldname")))
		if net_profit_loss:
			net_profit.append(net_profit_loss.get(p.get("fieldname")))

	datasets = []
	if income_data:
		datasets.append({"name": _("Income"), "values": income_data})
	if expense_data:
		datasets.append({"name": _("Expense"), "values": expense_data})
	if net_profit:
		datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"

	return chart

from frappe.desk.query_report import add_title_report, get_filters_data, build_xlsx_data
from openpyxl.utils import get_column_letter
def get_export_cost_center(filters):
	"""
	Generate grouped Profit & Loss data per non-group Cost Center.

	Returns a dict keyed by Cost Center name with:
	- label: Cost Center display name
	- columns: report columns for this run
	- data: report rows for this Cost Center
	- summary: report summary values
	"""
	base_filters = frappe._dict(filters or {})

	# Collect all non-group cost centers (scoped to company if provided)
	cc_filters = {"is_group": 0}
	if base_filters.get("company"):
		cc_filters["company"] = base_filters.company

	cost_centers = frappe.get_all(
		"Cost Center",
		filters=cc_filters,
		fields=["name", "cost_center_name"],
		order_by="name asc",
	)

	group_data = {}

	# add detail
	export_date = now()
	date_str = " "+get_datetime(export_date).strftime("%-d %B %y %H:%M:%S")
	report_name = "Profit and Loass Statement"
	title_report = add_title_report(report_name) 
	filter_report = get_filters_data(filters)

	for cc in cost_centers:
		# Prepare per-CC filters without mutating caller filters
		per_cc_filters = frappe._dict(base_filters.copy())
		per_cc_filters["cost_center"] = [cc.name]

		columns, data, _, _, report_summary = execute(per_cc_filters)
		temp = frappe._dict({
			"columns":columns,
			"result":data
		})
		xlsx_data, column_widths = build_xlsx_data(temp, [] , 1, ignore_visible_idx=1)
		xlsx_data = title_report + filter_report + [["Export date", date_str]] + xlsx_data

		group_data[cc.name] = {
			"label": cc.cost_center_name or cc.name,
			"columns": columns,
			"data": xlsx_data,
			"summary": report_summary,
			"column_widths":column_widths
		}

	return group_data


def _sanitize_sheet_name(name):
	name = (name or "Sheet").strip()
	# Excel invalid chars: : \ / ? * [ ]
	name = re.sub(r"[:\\/\?\*\[\]]", " ", name)
	if len(name) > 31:
		name = name[:31]
	return name or "Sheet"


@frappe.whitelist()
def export_with_cost_centers(filters=None):
	"""
	Build an XLSX where each Cost Center is a sheet containing its P&L data.

	Returns: { file_url: <saved file url> }
	"""
	if isinstance(filters, str):
		try:
			filters = frappe.parse_json(filters)
		except Exception:
			filters = {}

	filters['show_all_cost_centers'] = 0
	group_data  = get_export_cost_center(filters)

	if not openpyxl:
		frappe.throw("openpyxl is required to export XLSX")

	from frappe.utils.xlsxutils import ILLEGAL_CHARACTERS_RE, handle_html

	wb = openpyxl.Workbook(write_only=True)

	used_names = set()
	first_columns = None

	for cc_name, payload in (group_data or {}).items():
		label = payload.get("label") or cc_name
		sheet_name = _sanitize_sheet_name(label)

		# Ensure unique sheet names
		base = sheet_name
		idx = 1
		while sheet_name in used_names:
			suffix = f" {idx}"
			sheet_name = _sanitize_sheet_name((base[: (31 - len(suffix))]).rstrip() + suffix)
			idx += 1
		used_names.add(sheet_name)

		ws = wb.create_sheet(title=sheet_name)

		columns = payload.get("columns") or []
		if first_columns is None:
			first_columns = columns
		data_rows = payload.get("data") or []

		headers = [c.get("label") for c in columns]
		fields = [c.get("fieldname") for c in columns]
		ws.append(headers)

		# Set column width if provided
		column_widths = payload.get("column_widths")
		for i, column_width in enumerate(column_widths):
			if column_width:
				ws.column_dimensions[get_column_letter(i + 1)].width = column_width

		for row in data_rows:
			out = []
			if type(row) != list:
				for f in fields:
					val = (row or {}).get(f)
					if isinstance(val, str):
						try:
							val = handle_html(val)
							if isinstance(val, str):
								val = re.sub(ILLEGAL_CHARACTERS_RE, "", val)
						except Exception:
							pass
					out.append(val)
			else:
				out += row

			ws.append(out)

	bio = BytesIO()
	wb.save(bio)
	bio.seek(0)

	# Integrate with add_formulas to add formulas on all sheets
	try:
		from erpnext.accounts.report.balance_sheet_v2.balance_sheet_v2 import add_formulas
		# Build column_widths list from the first sheet's columns if available
		column_widths = None
		if first_columns:
			column_widths = []
			for col in first_columns:
				w = col.get("width")
				# Convert typical pixel widths to character widths approximation if needed
				if isinstance(w, (int, float)):
					# heuristic: 1 char ~ 8 px; clamp sensible range
					width_chars = max(6, min(80, int(float(w) / 8)))
				else:
					# fall back to label length approx
					label = col.get("label") or ""
					width_chars = max(8, min(50, len(str(label)) + 5))
				column_widths.append(width_chars)

		return add_formulas("Profit and Loss Statement", bio, column_widths=column_widths)

	except Exception:
		# Fallback: plain export if add_formulas unavailable
		now = now_datetime()
		date_str_title = now.strftime("%y%m%d_%H%M%S")
		frappe.response["filename"] = f"Profit and Loss by Cost Center_{date_str_title}.xlsx"
		frappe.response["filecontent"] = bio.getvalue()
		frappe.response["type"] = "binary"


@frappe.whitelist()
def get_export_with_cost_centers_url(filters=None):
	"""
	Helper to generate a URL for binary export so that the client
	can use frappe.call() first, then window.open() the returned URL.
	"""
	if isinstance(filters, str):
		try:
			filters = frappe.parse_json(filters)
		except Exception:
			filters = {}

	payload = quote(json.dumps(filters or {}))
	url = (
		"/api/method/erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement.export_with_cost_centers"
		f"?filters={payload}"
	)
	return {"url": url}
