# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now, nowdate

from erpnext.accounts.utils import FiscalYearError, get_fiscal_year

PL_FILTER = """(IFNULL(acc.report_type, '') != 'Profit and Loss'
	OR (gle.posting_date >= %(year_start)s AND gle.voucher_type != 'Period Closing Voucher'))"""

IN_SNAPSHOT = "gle.creation <= %(cutoff)s AND (gle.is_cancelled = 0 OR gle.modified > %(cutoff)s)"
ADDED_AFTER = "gle.creation > %(cutoff)s AND gle.is_cancelled = 0"
CANCELLED_AFTER = "gle.creation <= %(cutoff)s AND gle.is_cancelled = 1 AND gle.modified > %(cutoff)s"


class AccountBalanceSnapshot(Document):
	pass


def on_doctype_update():
	frappe.db.add_unique(
		"Account Balance Snapshot", ["company", "fiscal_year", "account"], "unique_company_fy_account"
	)


def _sum_gl_entries(company, year_start, condition, cutoff):
	rows = frappe.db.sql(
		f"""
		SELECT gle.account,
			SUM(gle.debit - gle.credit),
			SUM(gle.debit_in_account_currency - gle.credit_in_account_currency)
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE gle.company = %(company)s AND {condition} AND {PL_FILTER}
		GROUP BY gle.account
		""",
		{"company": company, "year_start": year_start, "cutoff": cutoff},
	)
	return {account: (flt(bal), flt(bal_ac)) for account, bal, bal_ac in rows}


def _get_current_fiscal_year(company):
	try:
		return get_fiscal_year(nowdate(), company=company, verbose=0)
	except FiscalYearError:
		return None


@frappe.whitelist()
def rebuild_account_balance_snapshots(company=None):
	frappe.only_for("System Manager")
	companies = [company] if company else frappe.get_all("Company", pluck="name")
	for name in companies:
		_rebuild_company_snapshot(name)
		frappe.db.commit()


def _rebuild_company_snapshot(company):
	fiscal_year = _get_current_fiscal_year(company)
	if not fiscal_year:
		return

	fiscal_year_name, year_start = fiscal_year[0], fiscal_year[1]
	cutoff = now()
	sums = _sum_gl_entries(company, year_start, IN_SNAPSHOT, cutoff)

	user = frappe.session.user
	values = [
		(
			frappe.generate_hash(length=10),
			user,
			cutoff,
			cutoff,
			user,
			0,
			company,
			account,
			fiscal_year_name,
			bal,
			bal_ac,
			cutoff,
		)
		for account, (bal, bal_ac) in sums.items()
	]

	frappe.db.delete("Account Balance Snapshot", {"company": company})
	if values:
		frappe.db.bulk_insert(
			"Account Balance Snapshot",
			[
				"name",
				"owner",
				"creation",
				"modified",
				"modified_by",
				"docstatus",
				"company",
				"account",
				"fiscal_year",
				"balance",
				"balance_in_account_currency",
				"cutoff",
			],
			values,
		)


def get_balances_from_snapshot(accounts, company, always_account_currency=False):
	"""
	Balance = snapshot + GL Entry added after cutoff - GL Entry cancelled after cutoff.
	Returns None when no usable snapshot exists so the caller can fall back to get_balance_on.
	"""
	fiscal_year = _get_current_fiscal_year(company)
	if not fiscal_year:
		return None

	fiscal_year_name, year_start = fiscal_year[0], fiscal_year[1]
	rows = frappe.db.get_all(
		"Account Balance Snapshot",
		filters={"company": company, "fiscal_year": fiscal_year_name},
		fields=["account", "balance", "balance_in_account_currency", "cutoff"],
	)
	if not rows:
		return None

	cutoff = rows[0].cutoff
	balances = {row.account: [flt(row.balance), flt(row.balance_in_account_currency)] for row in rows}

	for condition, sign in ((ADDED_AFTER, 1), (CANCELLED_AFTER, -1)):
		for account, (bal, bal_ac) in _sum_gl_entries(company, year_start, condition, cutoff).items():
			current = balances.setdefault(account, [0.0, 0.0])
			current[0] += sign * bal
			current[1] += sign * bal_ac

	names = [account["value"] for account in accounts]
	permitted = {
		d.name: d
		for d in frappe.get_list(
			"Account",
			filters={"name": ["in", names], "company": company},
			fields=["name", "lft", "rgt", "is_group"],
		)
	}

	ledgers = [
		(d.name, d.lft, d.rgt)
		for d in frappe.db.get_all(
			"Account", filters={"company": company, "is_group": 0}, fields=["name", "lft", "rgt"]
		)
	]

	company_currency = frappe.get_cached_value("Company", company, "default_currency")

	for account in accounts:
		meta = permitted.get(account["value"])
		if not meta:
			continue

		if meta.is_group:
			bal = bal_ac = 0.0
			for name, lft, rgt in ledgers:
				if lft >= meta.lft and rgt <= meta.rgt and name in balances:
					bal += balances[name][0]
					bal_ac += balances[name][1]
		else:
			bal, bal_ac = balances.get(meta.name, (0.0, 0.0))

		account["company_currency"] = company_currency
		account["balance"] = flt(bal)
		if always_account_currency or (
			account.get("account_currency") and account["account_currency"] != company_currency
		):
			account["balance_in_account_currency"] = flt(bal_ac)

	return accounts



@frappe.whitelist()
def get_account_balances(accounts, company):
	from json import loads

	from erpnext.accounts.utils import get_account_balances as get_account_balances_original

	if isinstance(accounts, str):
		accounts = loads(accounts)

	if not accounts:
		return []

	snapshot_balances = get_balances_from_snapshot(accounts, company)
	if snapshot_balances is not None:
		return snapshot_balances

	return get_account_balances_original(accounts, company)
