import frappe
from frappe.utils import add_days, get_first_day, getdate, nowdate

from erpnext.setup.utils import get_exchange_rate, get_exchange_rate_from_api1


def save_main_currency_rate():
	date = add_days(getdate(), -1)
	get_exchange_rate("SGD", "USD", date)
	get_exchange_rate("USD", "SGD", date)


def fetch_month_rate():
	# note: 06-05-2025
	# currently this will fetching at 1st each month
	# but not sure, the Bank's API already has the data when we call at weekend
	# because sometime 1st month is holiday!
	today = getdate(nowdate())
	first_date = get_first_day(today)

	if frappe.db.exists("Currency Exchange", {"date": first_date, "from_scheduler": 1}):
		return

	# test data:
	# if 1st date is holiday, then we will fetch again on tomorrow
	temp = get_exchange_rate_from_api1("USD", "SGD", today)
	if not temp.get("bank_date"):
		return

	# Step 1: Get all unique currency pairs that have ever been used in Currency Exchange
	pairs = frappe.get_all(
		"Currency Exchange",
		filters={"from_currency": ["!=", ""], "to_currency": ["!=", ""]},
		fields=["from_currency", "to_currency"],
		distinct=True,
	)

	# Step 2: Create a set of all recorded currency pairs
	pair_set = set((p["from_currency"], p["to_currency"]) for p in pairs)

	# Step 3: Add reversed pairs if they don't already exist
	reversed_pairs = set()
	for from_c, to_c in pair_set:
		if (to_c, from_c) not in pair_set:
			reversed_pairs.add((to_c, from_c))

	all_pairs = pair_set.union(reversed_pairs)

	# Step 4: For each unique pair, trigger get_exchange_rate for today's date
	for from_currency, to_currency in all_pairs:
		if from_currency == to_currency:
			continue
		try:
			get_exchange_rate(from_currency, to_currency, today, from_scheduler=1)
		except Exception:
			frappe.log_error(
				title=f"Currency Fetch Error: {from_currency} to {to_currency}",
				message=frappe.get_traceback(),
			)
