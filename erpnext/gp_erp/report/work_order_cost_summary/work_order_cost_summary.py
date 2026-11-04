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
			"fieldname": "work_order",
			"label": _("Work Order"),
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 120,
		},
		{
			"fieldname": "production_item",
			"label": _("Production Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 100,
		},
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 260,
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "cost_center",
			"label": _("Cost Center"),
			"fieldtype": "Data",
			"align": "left",
			"width": 180,
		},
		{
			"fieldname": "voucher_no",
			"label": _("Stock Entry"),
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "purpose",
			"label": _("Purpose"),
			"fieldtype": "Data",
			"width": 180,
		},
	]


def get_conditions(filters):
	conditions = ["gle.is_cancelled = 0", "gle.voucher_type = 'Stock Entry'"]
	if filters.get("company"):
		conditions.append("gle.company = %(company)s")
	if filters.get("from_date"):
		conditions.append("gle.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("gle.posting_date <= %(to_date)s")
	if filters.get("work_order"):
		conditions.append("se.work_order = %(work_order)s")
	if filters.get("production_item"):
		conditions.append("wo.production_item = %(production_item)s")

	return " AND ".join(conditions)


def get_data(filters):
	conditions = get_conditions(filters)

	rows = frappe.db.sql(
		"""
		SELECT
			se.work_order,
			wo.production_item,
			gle.account,
			gle.cost_center,
			gle.voucher_no,
			gle.posting_date,
			gle.debit,
			gle.credit,
			se.stock_entry_type_view AS purpose
		FROM `tabGL Entry` gle
			INNER JOIN `tabStock Entry` se ON se.name = gle.voucher_no
			INNER JOIN `tabWork Order` wo ON wo.name = se.work_order
		WHERE {conditions}
			AND se.work_order IS NOT NULL
			AND se.work_order != ''
		ORDER BY se.work_order, gle.posting_date, gle.creation
		""".format(conditions=conditions),
		filters,
		as_dict=1,
	)

	merge = int(filters.get("merge_summary") or 0)

	# group ledger rows per work order, preserving order of appearance
	grouped = []
	index = {}
	for r in rows:
		if r.work_order not in index:
			index[r.work_order] = len(grouped)
			grouped.append((r.work_order, r.production_item, []))
		grouped[index[r.work_order]][2].append(r)

	data = []
	cost_accounts = set()
	for i, (work_order, production_item, wo_rows) in enumerate(grouped):
		if i > 0:
			data.append({})  # blank spacer row between work orders

		display_rows = _merge_rows(wo_rows) if merge else wo_rows

		wo_debit = wo_credit = 0.0
		for j, r in enumerate(display_rows):
			wo_debit += flt(r.get("debit"))
			wo_credit += flt(r.get("credit"))
			# collect P&L cost accounts (expense/COGS: 5xxxx/6xxxx) used by WOs
			acct = r.get("account")
			if acct and str(acct)[0] in ("5", "6"):
				cost_accounts.add(acct)
			data.append({
				# show work order / production item only on the first row
				"work_order": work_order if j == 0 else None,
				"production_item": production_item if j == 0 else None,
				"account": r.get("account"),
				"cost_center": r.get("cost_center"),
				"voucher_no": r.get("voucher_no"),
				"purpose": r.get("purpose"),
				"posting_date": r.get("posting_date"),
				"debit": flt(r.get("debit")),
				"credit": flt(r.get("credit")),
			})

		data.append(_subtotal_row(work_order, wo_debit, wo_credit))

	# append Journal Entry payments that use the same cost accounts
	je_rows = get_journal_entries(filters, cost_accounts)
	if merge:
		je_rows = _merge_rows(je_rows)
	if je_rows:
		data.append({})  # spacer
		data.append({"work_order": _("Actual Payments (Journal Entries)")})
		je_debit = je_credit = 0.0
		for r in je_rows:
			je_debit += flt(r.get("debit"))
			je_credit += flt(r.get("credit"))
			data.append({
				"account": r.get("account"),
				"cost_center": r.get("cost_center"),
				"voucher_no": r.get("voucher_no"),
				"purpose": "Journal Entry",
				"posting_date": r.get("posting_date"),
				"debit": flt(r.get("debit")),
				"credit": flt(r.get("credit")),
			})
		data.append(_subtotal_row(_("Journal Entries"), je_debit, je_credit))

	return data


def get_journal_entries(filters, cost_accounts):
	"""Journal Entry legs that use the same cost accounts the work orders use
	(e.g. actual salary/utilities payments against 620001/650101). These are
	not linked to a specific work order, so they are shown once at the bottom."""
	if not cost_accounts:
		return []

	conditions = ["gle.is_cancelled = 0", "gle.voucher_type = 'Journal Entry'"]
	if filters.get("company"):
		conditions.append("gle.company = %(company)s")
	if filters.get("from_date"):
		conditions.append("gle.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("gle.posting_date <= %(to_date)s")

	args = dict(filters)
	args["cost_accounts"] = tuple(cost_accounts)

	return frappe.db.sql(
		"""
		SELECT
			gle.account,
			gle.cost_center,
			gle.voucher_no,
			gle.posting_date,
			gle.debit,
			gle.credit
		FROM `tabGL Entry` gle
		WHERE {conditions}
			AND gle.account IN %(cost_accounts)s
		ORDER BY gle.account, gle.posting_date, gle.creation
		""".format(conditions=" AND ".join(conditions)),
		args,
		as_dict=1,
	)


def _merge_rows(wo_rows):
	"""Merge ledger rows with the same account + cost center, netting debit and
	credit (mirrors GL's process_gl_map merge_entries behaviour). Voucher and
	purpose are dropped since a merged line may span multiple stock entries."""
	merged = {}
	order = []
	for r in wo_rows:
		key = (r.get("account"), r.get("cost_center"))
		if key not in merged:
			merged[key] = {
				"account": r.get("account"),
				"cost_center": r.get("cost_center"),
				"voucher_no": None,
				"purpose": None,
				"posting_date": None,
				"debit": 0.0,
				"credit": 0.0,
			}
			order.append(key)
		merged[key]["debit"] += flt(r.get("debit"))
		merged[key]["credit"] += flt(r.get("credit"))

	# net debit/credit so only one side remains, like GL merge
	result = []
	for key in order:
		m = merged[key]
		net = flt(m["debit"]) - flt(m["credit"])
		m["debit"] = net if net > 0 else 0.0
		m["credit"] = -net if net < 0 else 0.0
		result.append(m)
	return result


def _subtotal_row(work_order, debit, credit):
	return {
		"account": _("Total for {0}").format(work_order),
		"debit": flt(debit),
		"credit": flt(credit),
	}
