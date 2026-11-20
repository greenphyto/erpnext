import frappe
from frappe.utils import flt, getdate

COMPANY = "Greenphyto Pte Ltd"
ACCOUNT_NUMBERS = ("200022", "200023", "200024")
UPTO_DATE = "2026-10-31"
SUBMIT = False


def get_residuals():
	accounts = frappe.db.sql_list(
		"select name from `tabAccount` where company = %s and account_number in %s",
		(COMPANY, ACCOUNT_NUMBERS),
	)
	return frappe.db.sql(
		"""
		SELECT
			account,
			party,
			against_voucher_type,
			against_voucher,
			ROUND(SUM(debit - credit), 2) AS sgd,
			ROUND(SUM(debit_in_account_currency - credit_in_account_currency), 2) AS acc_ccy,
			MAX(posting_date) AS last_date
		FROM `tabGL Entry`
		WHERE company = %(company)s
			AND account IN %(accounts)s
			AND party_type = 'Supplier'
			AND is_cancelled = 0
			AND posting_date <= %(upto)s
			AND IFNULL(against_voucher, '') != ''
		GROUP BY account, party, against_voucher_type, against_voucher
		HAVING ABS(acc_ccy) < 0.005 AND ABS(sgd) >= 0.005
		ORDER BY account, party, against_voucher
		""",
		{"company": COMPANY, "accounts": accounts, "upto": UPTO_DATE},
		as_dict=True,
	)


def execute():
	gain_loss_account, cost_center = frappe.db.get_value(
		"Company", COMPANY, ["exchange_gain_loss_account", "cost_center"]
	)

	by_currency = {}
	for r in get_residuals():
		currency = frappe.db.get_value("Account", r.account, "account_currency")
		by_currency.setdefault(currency, []).append(r)

	created = []
	for currency, rows in sorted(by_currency.items()):
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Exchange Gain Or Loss"
		je.company = COMPANY
		je.posting_date = getdate(UPTO_DATE)
		je.multi_currency = 1
		je.currency_base = currency
		je.user_remark = f"Rounding difference {currency} payable accounts as at {UPTO_DATE}"

		net = 0.0
		for r in rows:
			diff = flt(r.sgd, 2)
			net += diff
			je.append(
				"accounts",
				{
					"account": r.account,
					"party_type": "Supplier",
					"party": r.party,
					"account_currency": currency,
					"exchange_rate": 0,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": 0,
					"debit_in_currency_base": 0,
					"credit_in_currency_base": 0,
					"debit": abs(diff) if diff < 0 else 0,
					"credit": diff if diff > 0 else 0,
					"cost_center": cost_center,
					"reference_type": r.against_voucher_type,
					"reference_name": r.against_voucher,
					"user_remark": f"{r.against_voucher} {diff:+.2f} SGD",
				},
			)

		net = flt(net, 2)
		if net:
			je.append(
				"accounts",
				{
					"account": gain_loss_account,
					"exchange_rate": 1,
					"debit_in_account_currency": net if net > 0 else 0,
					"credit_in_account_currency": abs(net) if net < 0 else 0,
					"debit": net if net > 0 else 0,
					"credit": abs(net) if net < 0 else 0,
					"cost_center": cost_center,
				},
			)

		je.insert()
		if SUBMIT:
			je.submit()
		created.append((je.name, currency, len(rows), net))

	for row in created:
		print(row)
