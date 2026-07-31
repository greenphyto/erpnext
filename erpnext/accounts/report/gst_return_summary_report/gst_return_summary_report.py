import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	return [
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 300},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "tax_amount", "label": _("Tax Amount"), "fieldtype": "Currency", "width": 150},
	]


def get_data(filters):
	company = filters.get("company")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	data = []

	sales_data = get_sales_data(company, from_date, to_date)
	data.append({"description": _("Standard-Rated Supplies"), "amount": sales_data.get("taxable_amount", 0), "tax_amount": sales_data.get("tax_amount", 0)})

	purchase_data = get_purchase_data(company, from_date, to_date)
	data.append({"description": _("Standard-Rated Purchases"), "amount": purchase_data.get("taxable_amount", 0), "tax_amount": purchase_data.get("tax_amount", 0)})

	return data


def get_sales_data(company, from_date, to_date):
	result = frappe.db.sql("""
		SELECT
			COALESCE(SUM(si.base_net_total), 0) as taxable_amount,
			COALESCE(SUM(si.base_total_taxes_and_charges), 0) as tax_amount
		FROM `tabSales Invoice` si
		WHERE si.company = %s
			AND si.posting_date BETWEEN %s AND %s
			AND si.docstatus = 1
	""", (company, from_date, to_date), as_dict=True)

	return result[0] if result else {"taxable_amount": 0, "tax_amount": 0}


def get_purchase_data(company, from_date, to_date):
	result = frappe.db.sql("""
		SELECT
			COALESCE(SUM(pi.base_net_total), 0) as taxable_amount,
			COALESCE(SUM(pi.base_total_taxes_and_charges), 0) as tax_amount
		FROM `tabPurchase Invoice` pi
		WHERE pi.company = %s
			AND pi.posting_date BETWEEN %s AND %s
			AND pi.docstatus = 1
	""", (company, from_date, to_date), as_dict=True)

	return result[0] if result else {"taxable_amount": 0, "tax_amount": 0}
