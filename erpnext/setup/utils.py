# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import add_days, cstr, flt, formatdate, get_datetime, get_datetime_str, get_first_day, nowdate
from frappe.utils.data import getdate, now_datetime
from frappe.utils.nestedset import get_root_of

from erpnext import get_default_company


def before_tests():
	frappe.clear_cache()
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	if not frappe.db.a_row_exists("Company"):
		current_year = now_datetime().year
		setup_complete(
			{
				"currency": "USD",
				"full_name": "Test User",
				"company_name": "Wind Power LLC",
				"timezone": "America/New_York",
				"company_abbr": "WP",
				"industry": "Manufacturing",
				"country": "United States",
				"fy_start_date": f"{current_year}-01-01",
				"fy_end_date": f"{current_year}-12-31",
				"language": "english",
				"company_tagline": "Testing",
				"email": "test@erpnext.com",
				"password": "test",
				"chart_of_accounts": "Standard",
			}
		)

	_setup_test_company()

	frappe.db.sql("delete from `tabItem Price`")

	_enable_all_roles_for_admin()

	set_defaults_for_tests()

	frappe.db.commit()


def _setup_test_company():
	import json
	import os

	test_records_path = os.path.join(
		os.path.dirname(__file__), "doctype", "company", "test_records.json"
	)
	with open(test_records_path) as f:
		test_companies = json.load(f)

	_ensure_holiday_list()

	for company_data in test_companies:
		company_name = company_data.get("company_name")
		if frappe.db.exists("Company", company_name):
			continue
		try:
			company = frappe.get_doc(company_data)
			company.flags.ignore_links = True
			company.insert(ignore_if_duplicate=True)
			frappe.db.commit()
		except Exception as e:
			print(f"_setup_test_company: Failed to create {company_name}: {e}")
			frappe.db.rollback()
			frappe.clear_messages()


def _ensure_holiday_list():
	if frappe.db.exists("Holiday List", "_Test Holiday List"):
		return
	from datetime import date
	current_year = now_datetime().year
	holiday_list = frappe.get_doc({
		"doctype": "Holiday List",
		"holiday_list_name": "_Test Holiday List",
		"from_date": f"{current_year}-01-01",
		"to_date": f"{current_year}-12-31",
	})
	holiday_list.insert(ignore_if_duplicate=True)
	frappe.db.commit()


def get_pegged_currencies():
	pegged_currencies = frappe.get_all(
		"Pegged Currency Details",
		filters={"parent": "Pegged Currencies"},
		fields=["source_currency", "pegged_against", "pegged_exchange_rate"],
	)

	pegged_map = {
		currency.source_currency: {
			"pegged_against": currency.pegged_against,
			"ratio": flt(currency.pegged_exchange_rate),
		}
		for currency in pegged_currencies
	}
	return pegged_map


def get_pegged_rate(pegged_map, from_currency, to_currency, transaction_date=None):
	from_entry = pegged_map.get(from_currency)
	to_entry = pegged_map.get(to_currency)

	if from_currency in pegged_map and to_currency in pegged_map:
		# Case 1: Both are present and pegged to same bases
		if from_entry["pegged_against"] == to_entry["pegged_against"]:
			return (1 / from_entry["ratio"]) * to_entry["ratio"]

		# Case 2: Both are present but pegged to different bases
		base_from = from_entry["pegged_against"]
		base_to = to_entry["pegged_against"]
		base_rate = get_exchange_rate(base_from, base_to, transaction_date)

		if not base_rate:
			return None

		return (1 / from_entry["ratio"]) * base_rate * to_entry["ratio"]

	# Case 3: from_currency is pegged to to_currency
	if from_entry and from_entry["pegged_against"] == to_currency:
		return flt(from_entry["ratio"])

	# Case 4: to_currency is pegged to from_currency
	if to_entry and to_entry["pegged_against"] == from_currency:
		return 1 / flt(to_entry["ratio"])

	""" If only one entry exists but doesn’t match pegged currency logic, return None """
	return None


@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency, transaction_date=None, args=None, err_journal=False, from_scheduler=False, force=False):
	if not (from_currency and to_currency):
		# manqala 19/09/2016: Should this be an empty return or should it throw and exception?
		return
	if from_currency == to_currency:
		return 1
	settingscheck = frappe.get_cached_doc("Currency Exchange Settings")
	
	if settingscheck.use_rate_as_first_day_of_month_rate and not err_journal:
		first_day = get_first_day(transaction_date)
		if getdate(transaction_date) == first_day:
			transaction_date = add_days(transaction_date, -1)
		else:
			transaction_date = first_day

	if settingscheck.api_endpoint.find("mas.gov.sg") > -1:
		from_currency = from_currency.lower()
		to_currency = to_currency.lower()
		listofcurrency = ["cny", "hkd","inr","idr","jpy","krw","myr","twd","php","qar","sar","thb","aed","ynd"]
		if from_currency in listofcurrency:
			to_currency = to_currency
	if not transaction_date:
		transaction_date = nowdate()
	
	currency_settings = frappe.get_doc("Accounts Settings").as_dict()
	allow_stale_rates = currency_settings.get("allow_stale")

	filters = [
		["date", "<=", get_datetime_str(transaction_date)],
		["from_currency", "=", from_currency],
		["to_currency", "=", to_currency],
	]

	if args == "for_buying":
		filters.append(["for_buying", "=", "1"])
	elif args == "for_selling":
		filters.append(["for_selling", "=", "1"])

	if not allow_stale_rates:
		stale_days = currency_settings.get("stale_days")
		checkpoint_date = add_days(transaction_date, -stale_days)
		filters.append(["date", ">", get_datetime_str(checkpoint_date)])

	# cksgb 19/09/2016: get last entry in Currency Exchange with from_currency and to_currency.
	entries = frappe.get_all(
		"Currency Exchange", fields=["exchange_rate", "date"], filters=filters, order_by="date desc", limit=1
	)
	if entries:
		data = entries[0]
		if getdate(data.date) != getdate(transaction_date) or force:
			return get_exchange_rate_from_api(from_currency, to_currency, transaction_date, settingscheck, from_scheduler=from_scheduler)

		return flt(data.exchange_rate)
	
	return get_exchange_rate_from_api(from_currency, to_currency, transaction_date, settingscheck, from_scheduler=from_scheduler)

def format_ces_api(data, param):
	return data.format(
		transaction_date=param.get("transaction_date"),
		to_currency=param.get("to_currency"),
		from_currency=param.get("from_currency"),
	)


def enable_all_roles_and_domains():
	"""enable all roles and domain for testing"""
	_enable_all_roles_for_admin()


def _enable_all_roles_for_admin():
	from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to

	all_roles = set(frappe.db.get_values("Role", pluck="name"))
	admin_roles = set(
		frappe.db.get_values("Has Role", {"parent": "Administrator"}, fieldname="role", pluck="role")
	)

	if all_roles.difference(admin_roles):
		add_all_roles_to("Administrator")


def set_defaults_for_tests():
	defaults = {
		"customer_group": get_root_of("Customer Group"),
		"territory": get_root_of("Territory"),
	}
	frappe.db.set_single_value("Selling Settings", defaults)
	for key, value in defaults.items():
		frappe.db.set_default(key, value)
	frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 0)


def insert_record(records):
	from frappe.desk.page.setup_wizard.setup_wizard import make_records

	make_records(records)


def welcome_email():
	site_name = get_default_company() or "ERPNext"
	title = _("Welcome to {0}").format(site_name)
	return title


def identity(x, *args, **kwargs):
	"""Used for redefining the translation function to return the string as is.

	We want to create english records but still mark the strings as translatable.
	E.g. when the respective DocTypes have 'Translate Link Fields' enabled or
	we're creating custom fields.

	Use like this: `from erpnext.setup.utils import identity as _`
	"""
	return x


def save_currency_exchange(from_currency, to_currency, date="", rate=0, fetch_on="", bank_date="", from_scheduler=0):
	from_currency = from_currency.upper()
	to_currency = to_currency.upper()
	
	date = getdate(date)
	if not rate:
		data = get_exchange_rate_from_api(from_currency, to_currency, date)
		rate = data.get("rate")
		fetch_on = data.get("fetch_on")
		bank_date = data.get("bank_date")
	
	params = {
		"date":date,
		"from_currency": from_currency,
		"to_currency": to_currency
	}
	if frappe.db.exists("Currency Exchange", params) or not rate:
		return

	if not frappe.db.get_single_value("Accounts Settings", "save_fetched_currency_exchange_rates"):
		return
	
	doc = frappe.new_doc("Currency Exchange")
	doc.update(params)
	doc.exchange_rate = rate
	doc.fetch_on = fetch_on
	doc.bank_date = bank_date
	doc.from_scheduler = cint(from_scheduler)
	doc.insert(ignore_if_duplicate=1)

	return doc.name


def get_exchange_rate_from_api1(from_currency, to_currency, transaction_date, settingscheck=None, dummy={}):
	from_currency = from_currency.lower()
	to_currency = to_currency.lower()
	data = {
		"fetch_on": cstr(now_datetime()),
		"bank_date":"",
		"rate":0
	}
	cur_date = getdate(nowdate())
	
	# overide date if furture date
	if getdate(transaction_date) > cur_date:
		transaction_date = cur_date

	try:
		idx = 0
		for i in range(7):
			transaction_date=add_days(cur_date, idx*-1)
			settings = frappe.get_cached_doc("Currency Exchange Settings")
			if settings.api_endpoint.find("mas.gov.sg") > -1:
				weekday = getdate(transaction_date).strftime('%A')
				if weekday=="Sunday":
					idx += 2
					transaction_date=add_days(cur_date, idx*-1)
				elif weekday=="Saturday" :
					idx += 1
					transaction_date=add_days(cur_date, idx*-1)
				else:
					idx += 1

			cache = frappe.cache()
			key = "currency_exchange_rate_{0}:{1}:{2}".format(transaction_date, from_currency, to_currency)
			value = flt(cache.get(key))

			if not value or 1:
				import requests

				req_params = {
					"transaction_date": transaction_date,
				}
				params = {}
				for row in settings.req_params:
					params[row.key] = format_ces_api(row.value, req_params)

				headers = {
					"accept": "application/json"
					}

				for row in settings.header_params:
					headers[row.key] = row.value.lower().format(
						transaction_date=nowdate(), to_currency="SGD", from_currency="USD"
					).lower()

				if not dummy:
					url = format_ces_api(settings.api_endpoint, req_params)
					response = requests.get(url, params=params, headers=headers)
					# expire in 6 hours
					if response.status_code != 200:
						idx += 1
						continue
					result = response.json()
				else:
					result = dummy

				if not result or not result['elements']:
					idx += 1
					continue

				if not from_currency in req_params:
					req_params['from_currency'] = from_currency.lower()
				if not to_currency in req_params:
					req_params['to_currency'] = to_currency.lower()

				value = result
				for res_key in settings.result_key:
					if  isinstance(value, dict):
						value = value[format_ces_api(str(res_key.key), req_params)]
					elif isinstance(value,list):
						k = format_ces_api(str(res_key.key.lower()), req_params)
						for ky, val in value[0].items():
							if ky == "end_of_day":
								data["bank_date"] = val

						if k in value[0]:
							value = flt(value[0][k])
						elif k + "_100" in value[0]:
							value =  flt(value[0][k + "_100"]) / 100
						else:
							# try different
							parts = k.split("_")
							if len(parts) == 2: 
								base, quote = parts
								rev_key = f"{quote}_{base}"
								rev_key_100 = f"{quote}_{base}_100"

								if rev_key in value[0]:
									value =  1 / flt(value[0][rev_key])
								elif rev_key_100 in value[0]:
									value = 100 / flt(value[0][rev_key_100])
						
				cache.setex(name=key, time=21600, value=flt(value))

				if value:
					break

			else:
				break
		
		data["rate"] = flt(value)
		return data
	except Exception as e:
		frappe.log_error("Unable to fetch exchange rate from API")
		frappe.log_error(e)
		return data
		
# unused


def get_exchange_rate_from_api2(from_currency, to_currency, transaction_date, settingscheck=None):
	data = {
		"fetch_on":cstr(now_datetime()),
		"bank_date":"",
		"rate":0
	}
	try:
		cache = frappe.cache()
		key = "currency_exchange_rate_{0}:{1}:{2}".format(transaction_date, from_currency, to_currency)
		value = cache.get(key)

		if not value or 1:
			import requests
			date_format = getdate(transaction_date).strftime("%Y-%m-%d")
			url = "https://api.frankfurter.dev/v1/{}?base={}&symbols={}".format(date_format, from_currency.upper(), to_currency.upper())
			response = requests.get(url)
			# expire in 6 hours
			response.raise_for_status()
			res = response.json()
			if "rates" in res:
				value = flt(res['rates'].get(to_currency.upper()))

			cache.setex(name=key, time=21600, value=flt(value))
			data["rate"] = flt(value)
			data["bank_date"] = res.get("date")
		
		return data
	except:
		return data
