import frappe
from frappe.utils import getdate, add_months, get_first_day, get_last_day


def execute(filters=None):
	filters = frappe._dict(filters or {})
	controlled = control_filters(filters)
	columns = get_columns(filters)
	data = get_data(filters, controlled)
	return columns, data


def control_filters(filters):
	year = filters.get("year", str(getdate().year))
	month = filters.get("month", "01")
	to_month = filters.get("to_month", month)
	company = filters.get("company")

	period_start_date = getdate(f"{year}-{month}-01")
	period_end_date = get_last_day(getdate(f"{year}-{to_month}-01"))

	return {
		"period_start_date": period_start_date,
		"period_end_date": period_end_date,
		"company": company,
	}


def get_columns(filters):
	return [
		{"fieldname": "account", "label": "Account", "fieldtype": "Link", "options": "Account", "width": 300},
		{"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 150},
	]


def get_data(filters, controlled):
	return []
