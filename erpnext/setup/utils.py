# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_datetime_str, nowdate, getdate
from frappe.utils.data import now_datetime
from frappe.utils.nestedset import get_ancestors_of, get_root_of  # noqa
import datetime
import calendar
from erpnext import get_default_company


def before_tests():
	frappe.clear_cache()
	# complete setup if missing
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

	frappe.db.sql("delete from `tabItem Price`")

	_enable_all_roles_for_admin()

	set_defaults_for_tests()

	frappe.db.commit()



@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency, transaction_date=None, args=None):
	if not (from_currency and to_currency):
		# manqala 19/09/2016: Should this be an empty return or should it throw and exception?
		return
	if from_currency == to_currency:
		return 1
	settingscheck = frappe.get_cached_doc("Currency Exchange Settings")
	if settingscheck.api_endpoint.find("mas.gov.sg") > -1:
		from_currency = from_currency.lower()
		to_currency = to_currency.lower()
		listofcurrency = ["cny", "hkd","inr","idr","jpy","krw","myr","twd","php","qar","sar","thb","aed","ynd"]
		if from_currency in listofcurrency:
			to_currency = to_currency +"_100"
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
		"Currency Exchange", fields=["exchange_rate"], filters=filters, order_by="date desc", limit=1
	)
	if entries:
		data = entries[0]
		if getdate(data.date) != getdate(nowdate()):
			save_currency_exchange(from_currency, to_currency)

		return flt(data.exchange_rate)
	
	return get_exchange_rate_from_api(from_currency, to_currency, transaction_date, settingscheck)

def get_exchange_rate_from_api(from_currency, to_currency, transaction_date, settingscheck=None):
	value = get_exchange_rate_from_api1(from_currency, to_currency, transaction_date, settingscheck)
	if not value:
		value = get_exchange_rate_from_api2(from_currency, to_currency, transaction_date, settingscheck)
	
	if not value:
		frappe.log_error("Unable to fetch exchange rate")
		frappe.log_error(Exception)
		frappe.msgprint(
			_(
				"Unable to find exchange rate for {0} to {1} for key date {2}. Please create a Currency Exchange record manually"
			).format(from_currency, to_currency, transaction_date)
		)
		return 0.0

	return value

def get_exchange_rate_from_api1(from_currency, to_currency, transaction_date, settingscheck=None):
	try:
		cache = frappe.cache()
		key = "currency_exchange_rate_{0}:{1}:{2}".format(transaction_date, from_currency, to_currency)
		value = cache.get(key)
		if not value:
			import requests

			settings = frappe.get_cached_doc("Currency Exchange Settings")
			if settings.api_endpoint.find("mas.gov.sg") > -1:
				weekday = findDay(transaction_date)
				if (weekday=="Monday"):
					transaction_date=add_days(transaction_date, -3)
				elif  (weekday=="Sunday") :
					transaction_date=add_days(transaction_date, -2)
				else:
					transaction_date=add_days(transaction_date, -1)

			req_params = {
				"transaction_date": transaction_date,
				"from_currency": from_currency,
				"to_currency": to_currency,
			}
			params = {}
			for row in settings.req_params:
				params[row.key] = format_ces_api(row.value, req_params)
			response = requests.get(format_ces_api(settings.api_endpoint, req_params), params=params)
			# expire in 6 hours
			response.raise_for_status()
			value = response.json()
			for res_key in settings.result_key:
				if  isinstance(value,dict):
					value = value[format_ces_api(str(res_key.key), req_params)]
				elif  isinstance(value,list):
					value = value[0][format_ces_api(str(res_key.key.lower()), req_params)]
			if settingscheck.api_endpoint.find("mas.gov.sg") > -1:
				listofcurrency = ["cny", "hkd","inr","idr","jpy","krw","myr","twd","php","qar","sar","thb","aed","ynd"]
				if from_currency in listofcurrency:	
					value = flt(value) / 100	
			cache.setex(name=key, time=21600, value=flt(value))
			save_currency_exchange(from_currency, to_currency, transaction_date, value)
		return flt(value)
	except:
		return 0.0
		

def get_exchange_rate_from_api2(from_currency, to_currency, transaction_date, settingscheck=None):
	try:
		cache = frappe.cache()
		key = "currency_exchange_rate_{0}:{1}:{2}".format(transaction_date, from_currency, to_currency)
		value = cache.get(key)

		if not value or 1:
			import requests

			settings = frappe.get_cached_doc("Currency Exchange Settings")
			req_params = {
				"transaction_date": transaction_date,
				"from_currency": from_currency,
				"to_currency": to_currency,
			}
			params = {}
			for row in settings.req_params:
				params[row.key] = format_ces_api(row.value, req_params)
			response = requests.get(format_ces_api(settings.api_endpoint, req_params), params=params)
			# expire in 6 hours
			response.raise_for_status()
			value = response.json()
			for res_key in settings.result_key:
				value = value[format_ces_api(str(res_key.key), req_params)]
			cache.setex(name=key, time=21600, value=flt(value))
			save_currency_exchange(from_currency, to_currency, transaction_date, value)
	except:
		return 0.0

def save_currency_exchange(from_currency, to_currency, date="", rate=0):
	date = getdate(date)
	if not rate:
		rate = get_exchange_rate_from_api(from_currency, to_currency, date)
	
	params = {
		"date":date,
		"from_currency": from_currency,
		"to_currency": to_currency
	}
	if frappe.db.exists("Currency Exchange", params) or not rate:
		return

	if not frappe.db.get_single_value("Currency Exchange", "save_fetched_currency_exchange_rates"):
		return
	
	doc = frappe.new_doc("Currency Exchange")
	doc.update(params)
	doc.exchange_rate = rate
	doc.insert()

	return doc.name

def findDay(date):
    year,month,day = (int(i) for i in date.split('-'))   
    dayNumber = calendar.weekday(year, month, day)
    days =["Monday", "Tuesday", "Wednesday", "Thursday",
                         "Friday", "Saturday", "Sunday"]
    return (days[dayNumber])

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
