import frappe
from frappe.utils import add_days, getdate, nowdate, get_first_day
from erpnext.setup.utils import get_exchange_rate


def save_main_currency_rate():
	date = add_days(getdate(), -1)
	get_exchange_rate("SGD", "USD", date)
	get_exchange_rate("USD", "SGD", date)


def fetch_month_rate():
	today = getdate(nowdate())
	first_date = get_first_day(today)

	if frappe.db.exists("Currency Exchange", {"date": first_date, "from_scheduler": 1}):
		return

	rate = get_exchange_rate("USD", "SGD", today)
	if not rate:
		return

	pairs = frappe.get_all(
		"Currency Exchange",
		filters={"from_currency": ["!=", ""], "to_currency": ["!=", ""]},
		fields=["from_currency", "to_currency"],
		distinct=True,
	)

	pair_set = set((p["from_currency"], p["to_currency"]) for p in pairs)

	reversed_pairs = set()
	for from_c, to_c in pair_set:
		if (to_c, from_c) not in pair_set:
			reversed_pairs.add((to_c, from_c))

	all_pairs = pair_set.union(reversed_pairs)

	for from_currency, to_currency in all_pairs:
		if from_currency == to_currency:
			continue
		try:
			get_exchange_rate(from_currency, to_currency, today)
		except Exception as e:
			frappe.log_error(
				title=f"Currency Fetch Error: {from_currency} to {to_currency}",
				message=frappe.get_traceback(),
			)
