# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import copy
import frappe
from frappe import _
from frappe.utils import flt, cint

from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_period_list,
)
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute as pl_report

PREV_YEAR_KEY = "prev_year"

# ============================================================================
# ACCOUNT NUMBER MAP
# Daftar group account number yang ditampilkan di report.
# Format per group: ("group_label", "parent_acc_code")
# Children otomatis di-fetch dari database berdasarkan parent account.
# ============================================================================

ASSET_NON_CURRENT = []

ASSET_CURRENT = [
	("Accounts Receivable", "100020"),
	("Cash in Bank", "100030"),
	("Stock", "100050"),
	("Deposit & Prepayment", "100060"),
	("Due from Holding company", "100075"),
	("Duties and Taxes", "240000"),
]

LIABILITY_CURRENT = [
	("Account Payable", "200009"),
	("Accruals and Provision", "210000"),
	("Amount Due to Director", "230000"),
]

LIABILITY_NON_CURRENT = []


def get_prev_fiscal_year(fiscal_year):
	prev_fy = frappe.db.get_value(
		"Fiscal Year",
		{"year_end_date": ("<", frappe.db.get_value("Fiscal Year", fiscal_year, "year_start_date"))},
		"name",
		order_by="year_end_date desc"
	)
	return prev_fy


def get_all_account_numbers():
	numbers = set()
	for section in [ASSET_NON_CURRENT, ASSET_CURRENT, LIABILITY_CURRENT, LIABILITY_NON_CURRENT]:
		for label, acc_code in section:
			if acc_code:
				numbers.add(acc_code)
	return numbers


def get_children_accounts(company, parent_acc_code):
	parent_account = frappe.db.get_value("Account", {
		"company": company,
		"account_number": parent_acc_code,
	}, "name")
	if not parent_account:
		return []
	children = frappe.get_all("Account", filters={
		"company": company,
		"parent_account": parent_account,
		"is_group": 0,
	}, fields=["name", "account_number"], order_by="account_number")
	return children


def get_equity_accounts(company):
	equity_root = frappe.db.get_value("Account", {
		"company": company,
		"root_type": "Equity",
		"parent_account": ["is", "not set"],
	}, "name")
	if not equity_root:
		equity_root = frappe.db.get_value("Account", {
			"company": company,
			"root_type": "Equity",
			"is_group": 1,
		}, "name", order_by="lft asc")
	if not equity_root:
		return []
	children = frappe.get_all("Account", filters={
		"company": company,
		"root_type": "Equity",
		"is_group": 0,
	}, fields=["account_number"], order_by="account_number")
	return [c.account_number for c in children if c.account_number]


def fetch_balances_via_get_data(company, period_list, filters, ignore_closing_entries):
	acc_map = {}
	root_type_totals = {}

	for root_type, balance_must_be in [("Asset", "Debit"), ("Liability", "Credit"), ("Equity", "Credit")]:
		data = get_data(
			company, root_type, balance_must_be, period_list,
			only_current_fiscal_year=False,
			filters=filters,
			accumulated_values=filters.accumulated_values,
			ignore_closing_entries=ignore_closing_entries,
			filter_zero_value=False,
		)
		if data:
			total_row = data[-2] if len(data) >= 2 else {}
			root_type_totals[root_type] = {}
			for p in period_list:
				root_type_totals[root_type][p.key] = flt(total_row.get(p.key))

			for row in data:
				acc_number = row.get("acc_code") or ""
				if acc_number:
					acc_map[acc_number] = {"_account": row.get("account") or ""}
					for p in period_list:
						acc_map[acc_number][p.key] = flt(row.get(p.key))

	return acc_map, root_type_totals


def execute(filters=None):
	filters = frappe._dict(filters or {})

	fiscal_year = filters.get("fiscal_year") or filters.get("from_fiscal_year")
	if not fiscal_year:
		frappe.throw(_("Fiscal Year is required"))

	filters.from_fiscal_year = fiscal_year
	filters.to_fiscal_year = fiscal_year
	filters.filter_based_on = "Fiscal Year"
	filters.periodicity = "Yearly"
	filters.accumulated_values = 1

	period_list = get_period_list(
		filters.from_fiscal_year, filters.to_fiscal_year,
		filters.period_start_date, filters.period_end_date,
		filters.filter_based_on, filters.periodicity,
		company=filters.company, month=filters.month, to_month=filters.to_month,
	)

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

	ignore_closing_entries = filters.ignore_closing_entries

	acc_map, root_type_totals = fetch_balances_via_get_data(
		filters.company, period_list, filters, ignore_closing_entries
	)

	# Prev year
	prev_acc_map = {}
	prev_root_type_totals = {}
	prev_fy = get_prev_fiscal_year(filters.from_fiscal_year)
	prev_period_list = None
	if prev_fy:
		prev_filters = copy.deepcopy(filters)
		prev_filters.from_fiscal_year = prev_fy
		prev_filters.to_fiscal_year = prev_fy
		prev_period_list = get_period_list(
			prev_fy, prev_fy,
			prev_filters.period_start_date, prev_filters.period_end_date,
			prev_filters.filter_based_on, prev_filters.periodicity,
			company=prev_filters.company,
		)
		if prev_period_list:
			prev_acc_map, prev_root_type_totals = fetch_balances_via_get_data(
				filters.company, prev_period_list, prev_filters, ignore_closing_entries
			)

	# P/L data
	pl_data = get_pl_report_data(filters)
	prev_pl_data = {}
	if prev_fy:
		prev_pl_filters = copy.deepcopy(filters)
		prev_pl_filters.from_fiscal_year = prev_fy
		prev_pl_filters.to_fiscal_year = prev_fy
		prev_pl_data = get_pl_report_data(prev_pl_filters)

	hide_if_empty = cint(filters.get("hide_if_empty", 1))

	# Build report rows
	data = []

	# --- ASSETS ---
	data.append(section_row("Assets"))
	data.append(group_row("Current assets", ""))
	render_groups(data, ASSET_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list, filters.company, hide_if_empty)
	asset_total = get_root_total("Asset", root_type_totals, period_list, prev_root_type_totals, prev_period_list)
	data.append(total_row("Total Asset (Debit)", asset_total, period_list, currency))

	# --- LIABILITIES ---
	data.append({})
	data.append(section_row("Liabilities"))
	data.append(group_row("Current liabilities", ""))
	render_groups(data, LIABILITY_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list, filters.company, hide_if_empty)
	liability_total = get_root_total("Liability", root_type_totals, period_list, prev_root_type_totals, prev_period_list)
	data.append(total_row("Total Liability (Credit)", liability_total, period_list, currency))

	# --- EQUITY ---
	data.append({})
	data.append(section_row("Equity"))
	equity_children = get_equity_accounts(filters.company)
	for acc in equity_children:
		row = make_acc_row_with_fallback(acc, acc_map, period_list, prev_acc_map, prev_period_list, filters.company)
		if row:
			if hide_if_empty:
				has_val = any(flt(row.get(p.key)) for p in period_list) or flt(row.get(PREV_YEAR_KEY))
				if not has_val:
					continue
			row["indent"] = 1
			data.append(row)

	# P/L row
	pl_row_data = make_pl_row(pl_data, period_list, prev_pl_data, prev_period_list, currency)
	pl_row_data["indent"] = 0
	data.append(pl_row_data)

	equity_total = get_root_total("Equity", root_type_totals, period_list, prev_root_type_totals, prev_period_list)
	# Add P/L to equity total
	for p in period_list:
		equity_total[p.key] += flt(pl_row_data.get(p.key))
	equity_total[PREV_YEAR_KEY] += flt(pl_row_data.get(PREV_YEAR_KEY))
	data.append(total_row("Total Equity (Credit)", equity_total, period_list, currency))

	# Total (Credit)
	data.append({})
	data.append({})
	final = {}
	for p in period_list:
		final[p.key] = flt(liability_total.get(p.key)) + flt(equity_total.get(p.key))
	final[PREV_YEAR_KEY] = flt(liability_total.get(PREV_YEAR_KEY)) + flt(equity_total.get(PREV_YEAR_KEY))
	data.append(total_row("'Total (Credit)'", final, period_list, currency))

	# Columns
	from frappe.utils import getdate

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, company=filters.company
	)
	for col in columns:
		if col.get("fieldtype") == "Currency" and col.get("fieldname") != PREV_YEAR_KEY:
			selected_month_label = getdate(period_list[-1].to_date).strftime("%b %Y") if period_list else _("Selected Month")
			col["label"] = "{} ({})".format(selected_month_label, currency)

	if prev_fy:
		prev_year_label = "Dec {} ({})".format(getdate(period_list[-1].to_date).year - 1, currency)
	else:
		prev_year_label = _("Previous Year")
	columns.insert(2, {
		"fieldname": PREV_YEAR_KEY,
		"label": prev_year_label,
		"fieldtype": "Currency",
		"options": "currency",
		"width": 150,
	})

	return columns, data, None, None, None


# === Helper functions ===

def section_row(label):
	return {"account_name": label, "account": label, "is_bold": True, "indent": 0}

def group_row(label, acc_code):
	return {"account_name": label, "account": label, "acc_code": acc_code or "", "is_group": True, "is_bold": True, "indent": 1}

def total_row(label, totals, period_list, currency):
	indent = 1
	if label in ("Total Asset (Debit)", "Total Liability (Credit)", "Total Equity (Credit)", "'Total (Credit)'"):
		indent = 0
	row = {"account_name": label, "account": label, "is_bold": True, "currency": currency, "indent": indent}
	for p in period_list:
		row[p.key] = flt(totals.get(p.key))
	row[PREV_YEAR_KEY] = flt(totals.get(PREV_YEAR_KEY))
	return row

def make_acc_row(acc_code, acc_map, period_list, prev_acc_map, prev_period_list):
	if acc_code not in acc_map:
		return None
	acc_data = acc_map[acc_code]
	row = {
		"account": acc_data.get("_account", ""),
		"account_name": acc_data.get("_account", ""),
		"acc_code": acc_code,
		"indent": 3,
	}
	for p in period_list:
		row[p.key] = flt(acc_data.get(p.key))
	row[PREV_YEAR_KEY] = get_prev_val(acc_code, prev_acc_map, prev_period_list)
	return row

def make_acc_row_with_fallback(acc_code, acc_map, period_list, prev_acc_map, prev_period_list, company):
	if acc_code in acc_map:
		return make_acc_row(acc_code, acc_map, period_list, prev_acc_map, prev_period_list)
	account_name = frappe.db.get_value("Account", {
		"company": company,
		"account_number": acc_code,
	}, "name")
	if not account_name:
		return None
	row = {
		"account": account_name,
		"account_name": account_name,
		"acc_code": acc_code,
		"indent": 3,
	}
	for p in period_list:
		row[p.key] = 0
	row[PREV_YEAR_KEY] = get_prev_val(acc_code, prev_acc_map, prev_period_list)
	return row

def get_prev_val(acc_code, prev_acc_map, prev_period_list):
	if not prev_acc_map or not prev_period_list:
		return 0
	last_key = prev_period_list[-1].key
	return flt(prev_acc_map.get(acc_code, {}).get(last_key))

def get_root_total(root_type, root_type_totals, period_list, prev_root_type_totals, prev_period_list):
	totals = {}
	for p in period_list:
		totals[p.key] = flt(root_type_totals.get(root_type, {}).get(p.key))
	if prev_period_list:
		last_key = prev_period_list[-1].key
		totals[PREV_YEAR_KEY] = flt(prev_root_type_totals.get(root_type, {}).get(last_key))
	else:
		totals[PREV_YEAR_KEY] = 0
	return totals

def render_groups(data, groups, acc_map, period_list, prev_acc_map, prev_period_list, company, hide_if_empty=False):
	for label, acc_code in groups:
		if label == "_spacer":
			data.append({})
			continue

		children = get_children_accounts(company, acc_code)
		child_codes = [c.account_number for c in children]

		group_total = {}
		for p in period_list:
			group_total[p.key] = 0
		group_total[PREV_YEAR_KEY] = 0

		for acc in child_codes:
			for p in period_list:
				group_total[p.key] += flt(acc_map.get(acc, {}).get(p.key))
			group_total[PREV_YEAR_KEY] += get_prev_val(acc, prev_acc_map, prev_period_list)

		if hide_if_empty:
			has_value = any(flt(group_total.get(p.key)) for p in period_list) or flt(group_total.get(PREV_YEAR_KEY))
			if not has_value:
				continue

		grp_row = {
			"account_name": label,
			"account": label,
			"acc_code": acc_code or "",
			"is_group": True,
			"indent": 2,
		}
		for p in period_list:
			grp_row[p.key] = group_total[p.key]
		grp_row[PREV_YEAR_KEY] = group_total[PREV_YEAR_KEY]
		data.append(grp_row)

		for acc in child_codes:
			row = make_acc_row_with_fallback(acc, acc_map, period_list, prev_acc_map, prev_period_list, company)
			if row:
				if hide_if_empty:
					has_child_value = any(flt(row.get(p.key)) for p in period_list) or flt(row.get(PREV_YEAR_KEY))
					if not has_child_value:
						continue
				data.append(row)

def sum_groups_total(groups, acc_map, period_list, prev_acc_map, prev_period_list, company):
	totals = {}
	for p in period_list:
		totals[p.key] = 0
	totals[PREV_YEAR_KEY] = 0

	for label, acc_code in groups:
		if label == "_spacer":
			continue
		children = get_children_accounts(company, acc_code)
		child_codes = [c.account_number for c in children]
		for acc in child_codes:
			for p in period_list:
				totals[p.key] += flt(acc_map.get(acc, {}).get(p.key))
			totals[PREV_YEAR_KEY] += get_prev_val(acc, prev_acc_map, prev_period_list)

	return totals

def make_pl_row(pl_data, period_list, prev_pl_data, prev_period_list, currency):
	row = {
		"account_name": "'Profit / (Loss) for the Year'",
		"account": "'Profit / (Loss) for the Year'",
		"is_bold": True,
		"currency": currency,
	}
	for p in period_list:
		value = pl_data.get(p.key)
		row[p.key] = flt(value) if value is not None else 0
	if prev_pl_data and prev_period_list:
		last_key = prev_period_list[-1].key
		value = prev_pl_data.get(last_key)
		row[PREV_YEAR_KEY] = flt(value) if value is not None else 0
	else:
		row[PREV_YEAR_KEY] = 0
	return row

def get_pl_report_data(filters):
	pl_data = pl_report(filters)
	data = {}
	if len(pl_data) > 1 and pl_data[1]:
		for d in pl_data[1]:
			if d.get("profit_data"):
				data = d
	return data
