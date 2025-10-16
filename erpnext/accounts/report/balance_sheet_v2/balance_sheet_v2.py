# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt, cstr

from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)

from erpnext.accounts.utils import remove_account_number
from erpnext.accounts.report.utils import convert_wrap_report_data


def execute(filters=None):
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

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

	ignore_closing_entries = filters.ignore_closing_entries

	asset = get_data(
		filters.company,
		"Asset",
		"Debit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=ignore_closing_entries
	)

	liability = get_data(
		filters.company,
		"Liability",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=ignore_closing_entries
	)

	equity = get_data(
		filters.company,
		"Equity",
		"Credit",
		period_list,
		only_current_fiscal_year=False,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=ignore_closing_entries
	)

	provisional_profit_loss, total_credit = get_provisional_profit_loss(
		asset, liability, equity, period_list, filters.company, currency
	)

	message, opening_balance = check_opening_balance(asset, liability, equity)

	temp_data = []
	temp_data.extend(asset or [])
	temp_data.extend(liability or [])
	temp_data.extend(equity or [])

	data = []
	if filters.show_number_group:
		data = temp_data
	else:
		for d in temp_data:
			if d.get("is_group"):
				d['account_name'] = remove_account_number(d['account_name'])
				if frappe.flags.in_export:
					d['account_origin'] = cstr(d['account'])
					d['account'] = d['account_name']
					if not d.get('parent_account'):
						for key, val in d.items():
							if key not in ['account', 'account_name']:
								d[key] = None

			data.append(d)

	if opening_balance and round(opening_balance, 2) != 0:
		unclosed = {
			"account_name": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"account": "'" + _("Unclosed Fiscal Years Profit / Loss (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency,
		}
		for period in period_list:
			unclosed[period.key] = opening_balance
			if provisional_profit_loss:
				provisional_profit_loss[period.key] = provisional_profit_loss[period.key] - opening_balance

		unclosed["total"] = opening_balance
		data.append(unclosed)

	if provisional_profit_loss:
		data.append(provisional_profit_loss)
	if total_credit:
		data.append(total_credit)

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, company=filters.company
	)

	chart = get_chart_data(filters, columns, asset, liability, equity)

	report_summary = get_report_summary(
		period_list, asset, liability, equity, provisional_profit_loss, total_credit, currency, filters
	)

	if frappe.flags.in_export:
		convert_wrap_report_data(columns, data, precision=2)

	return columns, data, message, chart, report_summary


def get_provisional_profit_loss(
	asset, liability, equity, period_list, company, currency=None, consolidated=False
):
	provisional_profit_loss = {}
	total_row = {}
	if asset and (liability or equity):
		total = total_row_total = 0
		currency = currency or frappe.get_cached_value("Company", company, "default_currency")
		total_row = {
			"account_name": "'" + _("Total (Credit)") + "'",
			"account": "'" + _("Total (Credit)") + "'",
			"warn_if_negative": True,
			"currency": currency,
		}
		has_value = False

		for period in period_list:
			key = period if consolidated else period.key
			effective_liability = 0.0
			if liability:
				effective_liability += flt(liability[-2].get(key))
			if equity:
				effective_liability += flt(equity[-2].get(key))

			provisional_profit_loss[key] = flt(asset[-2].get(key)) - effective_liability
			total_row[key] = effective_liability + provisional_profit_loss[key]

			if provisional_profit_loss[key]:
				has_value = True

			provisional_profit_loss["total"] = flt(total)
			total += flt(provisional_profit_loss[key])

			total_row_total += flt(total_row[key])
			total_row["total"] = total_row_total

		if has_value:
			provisional_profit_loss.update(
				{
					"account_name": "'" + _("Profit / (Loss) for the Year") + "'",
					"account": "'" + _("Profit / (Loss) for the Year") + "'",
					"warn_if_negative": True,
					"currency": currency,
				}
			)

	return provisional_profit_loss, total_row


def check_opening_balance(asset, liability, equity):
	# Check if previous year balance sheet closed
	opening_balance = 0
	float_precision = cint(frappe.db.get_default("float_precision")) or 2
	if asset:
		opening_balance = flt(asset[-1].get("opening_balance", 0), float_precision)
	if liability:
		opening_balance -= flt(liability[-1].get("opening_balance", 0), float_precision)
	if equity:
		opening_balance -= flt(equity[-1].get("opening_balance", 0), float_precision)

	opening_balance = flt(opening_balance, float_precision)
	if opening_balance:
		return _("Previous Financial Year is not closed"), opening_balance
	return None, None


def get_report_summary(
	period_list,
	asset,
	liability,
	equity,
	provisional_profit_loss,
	total_credit,
	currency,
	filters,
	consolidated=False,
):

	net_asset, net_liability, net_equity, net_provisional_profit_loss = 0.0, 0.0, 0.0, 0.0

	if filters.get("accumulated_values"):
		period_list = [period_list[-1]]

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	for period in period_list:
		key = period if consolidated else period.key
		if asset:
			net_asset += asset[-2].get(key)
		if liability:
			net_liability += liability[-2].get(key)
		if equity:
			net_equity += equity[-2].get(key)
		if provisional_profit_loss:
			net_provisional_profit_loss += provisional_profit_loss.get(key)

	return [
		{"value": net_asset, "label": _("Total Asset"), "datatype": "Currency", "currency": currency},
		{
			"value": net_liability,
			"label": _("Total Liability"),
			"datatype": "Currency",
			"currency": currency,
		},
		{"value": net_equity, "label": _("Total Equity"), "datatype": "Currency", "currency": currency},
		{
			"value": net_provisional_profit_loss,
			"label": _("Profit / (Loss) for the Year"),
			"indicator": "Green" if net_provisional_profit_loss > 0 else "Red",
			"datatype": "Currency",
			"currency": currency,
		},
	]


def get_chart_data(filters, columns, asset, liability, equity):
	labels = [d.get("label") for d in columns[2:]]

	asset_data, liability_data, equity_data = [], [], []

	for p in columns[2:]:
		if asset:
			asset_data.append(asset[-2].get(p.get("fieldname")))
		if liability:
			liability_data.append(liability[-2].get(p.get("fieldname")))
		if equity:
			equity_data.append(equity[-2].get(p.get("fieldname")))

	datasets = []
	if asset_data:
		datasets.append({"name": _("Assets"), "values": asset_data})
	if liability_data:
		datasets.append({"name": _("Liabilities"), "values": liability_data})
	if equity_data:
		datasets.append({"name": _("Equity"), "values": equity_data})

	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	return chart

from frappe.utils.xlsxutils import make_xlsx
from openpyxl import load_workbook
from io import BytesIO
from frappe.utils import now_datetime
def add_formulas(report_name, xlsx_file):
	# Load workbook dari stream hasil make_xlsx
	stream = BytesIO(xlsx_file.getvalue())
	wb = load_workbook(stream)
	ws = wb.active
	# check parent vs child
	# start sum
	# end sum

	def is_child(cell_value):
		"""Kembalikan True jika teks diawali angka."""
		if not isinstance(cell_value, str):
			return False
		stripped = cell_value.strip()
		return stripped[:1].isdigit() 

	hierarchy = {} 
	h_level = {}

	start_modify = False
	cur_level = 1
	prev_type = ""
	prev_account = ""
	cur_group = []
	for row in range(2, ws.max_row + 1):
		account = cstr(ws[f"A{row}"].value).strip()
		if account == 'Assets':
			start_modify = True
		
		if not start_modify:
			continue
		
		h_level.setdefault(cur_level, {})
		if is_child(account):
			cur_type = "child"
			# CHILD → contoh: buat formula
			# ws[f"D{row}"] = f"=B{row}+C{row}+1000000000"
			print(f"Row {row}: {account} → CHILD")
			if prev_type == "parent":
				last_parent = cur_group[-1]
				h_level[cur_level][last_parent].append(account)
			elif prev_type == "child":
				last_parent = cur_group[-1]
				h_level[cur_level][last_parent].append(account)

		else:
			# PARENT
			cur_type = "parent"
			print(f"Row {row}: {account.strip()} → PARENT")
			if not prev_type:
				cur_group.append(account)
				h_level[cur_level].setdefault(account, [])
			elif prev_type == "parent":
				cur_group.append(account)
				h_level[cur_level].setdefault(last_parent, [])
				h_level[cur_level][last_parent].append(account)

				cur_level += 1
				h_level.setdefault(cur_level, {})
				h_level[cur_level].setdefault(account, [])
			elif prev_type == "child":
				# find prev parent list 1 level above
				cur_group.pop()
				cur_level -= 1
				last_parent = cur_group[-1]
				cur_group.append(account)
				h_level[cur_level][last_parent].append(account)

				cur_level += 1
				h_level.setdefault(cur_level, {})
				h_level[cur_level].setdefault(account, [])
				print(111)

		
		prev_type = cur_type
		prev_account = account
				
			
			

	output_stream = BytesIO()
	wb.save(output_stream)
	output_stream.seek(0)

	now = now_datetime()
	date_str_title = now.strftime(" %Y-%m-%d %H-%M-%S")

	frappe.response["filename"] = f"{report_name}-TEST-{date_str_title}.xlsx"
	frappe.response["filecontent"] = output_stream.getvalue()
	frappe.response["type"] = "binary"