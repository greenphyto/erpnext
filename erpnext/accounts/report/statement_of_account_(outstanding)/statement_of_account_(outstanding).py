# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa
from frappe.utils import add_days, add_months, format_date, getdate, today,get_last_day,add_to_date


def execute(filters=None):
	report = Report(filters)
	return report.execute()

class Report():
	def __init__(self, filters):
		self.filters = filters

	def setup_column(self):
		self.columns = [
			{"label": _("Date"), 			"fieldname": "posting_date", "fieldtype": "Date", "width": 120},
			{"label": _("Invoice"), 		"fieldname": "voucher_no",	 "fieldtype": "Link", "width": 200, "options":"Sales Invoice"},
			{"label": _("Customer PO"), 	"fieldname": "customer_po",	 "fieldtype": "Data", "width": 120 },
			{"label": _("Delivery Note"), 	"fieldname": "delivery_note","fieldtype": "Data", "width": 150 },
			{"label": _("Amount"), 			"fieldname": "debit",		 "fieldtype": "Currency", "width": 120},
		]

	def get_data(self):
		lastdayofmonth = get_last_day(add_to_date(today(), months=-1))
		objcompany = frappe.get_doc("Company", self.filters.company)
		lstAddress = frappe.db.get_list('Address', filters=[[
		"Dynamic Link","link_name","=", self.filters.company
			]],fields=['address_line1','city','pincode'])
		
		filters = frappe._dict(
			{
				"from_date": self.filters.from_date,
				"to_date": self.filters.to_date,
				"company": self.filters.company,
				"finance_book": self.filters.finance_book if self.filters.finance_book else None,
				"account": [self.filters.account] if self.filters.account else None,
				"party_type": "Customer",
				"party": [self.filters.customer],
				"presentation_currency": self.filters.currency,
				"group_by": self.filters.group_by,
				# "currency": self.filters.currency,
				"cost_center": self.filters.cost_center,
				"show_opening_entries": 0,
				"include_default_book_entries": 0,
				"StatementDate": today(),
				"LastDay": lastdayofmonth,
				"phone": objcompany.phone_no,
				"email": objcompany.email,
				"fax": objcompany.fax,
				"address": lstAddress[0].address_line1 if lstAddress else None,
				"zipcode":  lstAddress[0].pincode if lstAddress else None ,
				"city": lstAddress[0].city if lstAddress else None ,
			}
		)

		self.data = []
		self.totals = 0
		col, res = get_soa(filters)
		for d in res:
			if not d.get("voucher_type") or d.get("voucher_type") != "Sales Invoice":
				continue
			
			outstanding = frappe.get_value("Sales Invoice", d.voucher_no, "outstanding_amount")
			if outstanding == 0:
				continue
			
			self.totals += d.debit
			self.data.append(d)
		
		self.data.append({
			"delivery_note": "Total",
			"debit": self.totals
		})

	def execute(self):
		self.setup_column()
		self.get_data()

		return self.columns, self.data