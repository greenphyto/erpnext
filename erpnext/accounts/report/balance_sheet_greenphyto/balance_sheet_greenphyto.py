# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import copy
import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_period_list,
)
from erpnext.accounts.report.utils import convert_wrap_report_data
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute as pl_report

PREV_YEAR_KEY = "prev_year"

# ============================================================================
# ACCOUNT NUMBER MAP
# Daftar account number yang ditampilkan di report beserta urutannya.
# Format per group: ("group_label", "acc_code_group", ["child_acc_numbers"])
# Untuk edit: tambah/hapus account number di list, atau reorder groups.
# ============================================================================

ASSET_NON_CURRENT = [
	("Fixed Assets", "110001", [
		"110010", "110028", "110030", "110040", "110050", "110060", "110070", "110900",
	]),
	("Accumulated Depreciation", None, [
		"110510", "110528", "110530", "110540", "110550", "110560", "110570",
	]),
	("_spacer", None, None),
	("Intangible assets", None, [
		"110072", "110575",
	]),
	("Right-of-use assets", None, [
		"110003", "110004", "110020", "110512", "110513", "110520",
	]),
	("Investments", "100090", [
		"152038",
	]),
]

ASSET_CURRENT = [
	("Accounts Receivable", "100020", [
		"140000", "140010",
	]),
	("Cash in Bank", "100030", [
		"161020", "161022", "161024", "161092", "161100",
	]),
	("Stock", "100050", [
		"121100", "121102", "121103", "121104", "121107", "121111", "121113",
		"121120", "121123", "121125", "121127", "121128", "121129", "121130", "121131",
		"121134", "121135",
		"121301", "121302", "121400", "121500", "121600", "121700",
		"122000", "122100", "123110",
	]),
	("Deposit & Prepayment", "100060", [
		"144000", "144003", "144030", "144040",
	]),
	("GST- Input Tax", "100080", [
		"147000",
	]),
	("Duties and Taxes (GST receivables)", "240000", [
		"247000", "247100",
	]),
	("Contra Account (others)", "250000", []),
]

LIABILITY_CURRENT = [
	("Account Payable", "200009", [
		"200010", "200011", "200012", "200020", "200022", "200023", "200024", "200100",
	]),
	("Accruals and Provision", "210000", [
		"210010", "210020", "210030", "210040", "210042", "210050", "210060",
	]),
	("Lease liabilities", "220000", [
		"220010", "220020", "220030",
	]),
	("Borrowings", None, [
		"220040", "220042", "220043",
	]),
	("Amount Due to Director", "230000", [
		"230100", "250010",
	]),
	("Deferred income", None, []),
]

LIABILITY_NON_CURRENT = [
	("Other LT Liabilities", "260000", [
		"260010", "260016", "260020",
	]),
	("Long Term Lease Liabilities", "270000", [
		"270010", "270030",
	]),
	("Long Term Suppliers (UOB borrowings)", "280000", [
		"280010", "280020", "280024", "280030", "280040", "280050",
	]),
	("Deferred Income", "280070", None),
	("Convertible loan Liability", "290000", [
		"290010", "290020",
	]),
]

EQUITY_ACCOUNTS = ["300000", "310000", "320000", "340000"]


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
		for label, acc_code, children in section:
			if label == "_spacer":
				continue
			if acc_code:
				numbers.add(acc_code)
			if children:
				numbers.update(children)
	numbers.update(EQUITY_ACCOUNTS)
	return numbers


def fetch_gl_balances(company, period_list, filters, ignore_closing_entries):
	acc_numbers = get_all_account_numbers()

	all_accounts = frappe.get_all("Account", filters={
		"company": company,
		"account_number": ["in", list(acc_numbers)],
		"is_group": 0,
	}, fields=["name", "account_number"])

	account_names = [a.name for a in all_accounts]
	acc_num_map = {a.name: a.account_number for a in all_accounts}

	if not account_names:
		return {}

	from erpnext.accounts.report.financial_statements import get_gl_entries

	gl_entries = get_gl_entries(company, period_list[-1].from_date if period_list else None,
		period_list[-1].to_date if period_list else None, account_names, filters, ignore_closing_entries)

	# Build balance per account_number per period
	# We need accumulated balance, so get opening + period movements
	balances = {}
	for acc_name, entries in gl_entries.items():
		acc_number = acc_num_map.get(acc_name)
		if not acc_number:
			continue
		if acc_number not in balances:
			balances[acc_number] = {"_account": acc_name}
			for p in period_list:
				balances[acc_number][p.key] = 0

		for entry in entries:
			for p in period_list:
				if entry.posting_date <= p.to_date:
					balances[acc_number][p.key] += flt(entry.debit) - flt(entry.credit)

	return balances


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

	period_list = get_period_list(
		filters.from_fiscal_year, filters.to_fiscal_year,
		filters.period_start_date, filters.period_end_date,
		filters.filter_based_on, filters.periodicity,
		company=filters.company, month=filters.month, to_month=filters.to_month,
	)

	if not filters.get("accumulated_values"):
		frappe.throw(_("Accumulated Values must be set fo Balance Sheet report"))

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
			company=prev_filters.company, month=prev_filters.month, to_month=prev_filters.to_month,
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

	# Build report rows
	data = []

	# --- ASSETS ---
	data.append(section_row("Assets"))
	data.append(group_row("Non-Current Assets", "100000"))
	render_groups(data, ASSET_NON_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list)
	nc_total = sum_groups_total(ASSET_NON_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list)
	data.append(total_row("", nc_total, period_list, currency))

	data.append(group_row("Current assets", ""))
	render_groups(data, ASSET_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list)
	ca_total = sum_groups_total(ASSET_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list)
	data.append(total_row("", ca_total, period_list, currency))
	data.append({})

	asset_total = get_root_total("Asset", root_type_totals, period_list, prev_root_type_totals, prev_period_list)
	data.append(total_row("Total Asset (Debit)", asset_total, period_list, currency))
	data.append({})

	# --- LIABILITIES ---
	data.append(section_row("Liabilities"))
	data.append(group_row("Current liabilities", ""))
	render_groups(data, LIABILITY_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list)
	cl_total = sum_groups_total(LIABILITY_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list)
	data.append(total_row("", cl_total, period_list, currency))

	data.append(group_row("Non-Current liabities", ""))
	render_groups(data, LIABILITY_NON_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list)
	ncl_total = sum_groups_total(LIABILITY_NON_CURRENT, acc_map, period_list, prev_acc_map, prev_period_list)
	data.append(total_row("", ncl_total, period_list, currency))
	data.append({})

	liability_total = get_root_total("Liability", root_type_totals, period_list, prev_root_type_totals, prev_period_list)
	data.append(total_row("Total Liability (Credit)", liability_total, period_list, currency))
	data.append({})

	# --- EQUITY ---
	data.append(section_row("Equity"))
	for acc in EQUITY_ACCOUNTS:
		row = make_acc_row(acc, acc_map, period_list, prev_acc_map, prev_period_list)
		if row:
			data.append(row)

	# P/L row
	pl_row_data = make_pl_row(pl_data, period_list, prev_pl_data, prev_period_list, currency)
	data.append(pl_row_data)

	equity_total = get_root_total("Equity", root_type_totals, period_list, prev_root_type_totals, prev_period_list)
	# Add P/L to equity total
	for p in period_list:
		equity_total[p.key] += flt(pl_row_data.get(p.key))
	equity_total[PREV_YEAR_KEY] += flt(pl_row_data.get(PREV_YEAR_KEY))
	data.append(total_row("Total Equity (Credit)", equity_total, period_list, currency))
	data.append({})
	data.append({})

	# Total Liability + Equity
	final = {}
	for p in period_list:
		final[p.key] = flt(liability_total.get(p.key)) + flt(equity_total.get(p.key))
	final[PREV_YEAR_KEY] = flt(liability_total.get(PREV_YEAR_KEY)) + flt(equity_total.get(PREV_YEAR_KEY))
	data.append(total_row("Total Liability and Equity (Credit)", final, period_list, currency))

	# Columns
	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, company=filters.company
	)
	for col in columns:
		if col.get("fieldtype") == "Currency" and col.get("fieldname") != PREV_YEAR_KEY:
			col["label"] = "{} ({})".format(col["label"], currency)

	prev_year_label = "{} ({})".format(prev_fy or _("Previous Year"), currency)
	columns.insert(2, {
		"fieldname": PREV_YEAR_KEY,
		"label": prev_year_label,
		"fieldtype": "Currency",
		"options": "currency",
		"width": 150,
	})

	if frappe.flags.in_export:
		convert_wrap_report_data(columns, data, precision=2)

	return columns, data, None, None, None


# === Helper functions ===

def section_row(label):
	return {"account_name": label, "account": label, "is_bold": True}

def group_row(label, acc_code):
	return {"account_name": label, "account": label, "acc_code": acc_code or "", "is_group": True}

def total_row(label, totals, period_list, currency):
	row = {"account_name": label, "account": label, "is_bold": True, "currency": currency}
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
	}
	for p in period_list:
		row[p.key] = flt(acc_data.get(p.key))
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

def render_groups(data, groups, acc_map, period_list, prev_acc_map, prev_period_list):
	for label, acc_code, children in groups:
		if label == "_spacer":
			data.append({})
			continue

		if children is None:
			# Single account displayed as bold row
			row = make_acc_row(acc_code, acc_map, period_list, prev_acc_map, prev_period_list)
			if row:
				row["account_name"] = label
				row["is_bold"] = True
				data.append(row)
			continue

		# Group with children
		group_total = {}
		for p in period_list:
			group_total[p.key] = 0
		group_total[PREV_YEAR_KEY] = 0

		for acc in children:
			for p in period_list:
				group_total[p.key] += flt(acc_map.get(acc, {}).get(p.key))
			group_total[PREV_YEAR_KEY] += get_prev_val(acc, prev_acc_map, prev_period_list)

		# Also add acc_code itself if it has a value (group account with balance)
		if acc_code and acc_code in acc_map:
			for p in period_list:
				group_total[p.key] += flt(acc_map[acc_code].get(p.key))
			group_total[PREV_YEAR_KEY] += get_prev_val(acc_code, prev_acc_map, prev_period_list)

		grp_row = {
			"account_name": label,
			"account": label,
			"acc_code": acc_code or "",
			"is_group": True,
		}
		for p in period_list:
			grp_row[p.key] = group_total[p.key]
		grp_row[PREV_YEAR_KEY] = group_total[PREV_YEAR_KEY]
		data.append(grp_row)

		for acc in children:
			row = make_acc_row(acc, acc_map, period_list, prev_acc_map, prev_period_list)
			if row:
				data.append(row)

def sum_groups_total(groups, acc_map, period_list, prev_acc_map, prev_period_list):
	totals = {}
	for p in period_list:
		totals[p.key] = 0
	totals[PREV_YEAR_KEY] = 0

	for label, acc_code, children in groups:
		if label == "_spacer":
			continue
		if children is None:
			if acc_code and acc_code in acc_map:
				for p in period_list:
					totals[p.key] += flt(acc_map[acc_code].get(p.key))
				totals[PREV_YEAR_KEY] += get_prev_val(acc_code, prev_acc_map, prev_period_list)
			continue
		for acc in children:
			for p in period_list:
				totals[p.key] += flt(acc_map.get(acc, {}).get(p.key))
			totals[PREV_YEAR_KEY] += get_prev_val(acc, prev_acc_map, prev_period_list)
		if acc_code and acc_code in acc_map:
			for p in period_list:
				totals[p.key] += flt(acc_map[acc_code].get(p.key))
			totals[PREV_YEAR_KEY] += get_prev_val(acc_code, prev_acc_map, prev_period_list)

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
