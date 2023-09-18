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
		self.columns = []
		self.data = []
	
	def setup_filters(self):
		self.conditions = ""

		if self.filters.get("from_date") and self.filters.get("to_date"):
			self.conditions += " and si.posting_date between %(from_date)s and %(to_date)s "
		if self.filters.get("supplier"):
			self.conditions += " and si.supplier = %(supplier)s "
		if self.filters.get("customer"):
			self.conditions += " and si.customer = %(customer)s "
	
	def validate_filters(self):
		if self.filters.get("party_type")=="Supplier" and not self.filters.get("supplier"):
			return False
		elif self.filters.get("party_type")=="Customer" and not self.filters.get("customer"):
			return False
		
		return True

	def setup_query(self):
		self.query = "po_no"
		self.doctype = "Sales Invoice"
		if self.filters.party_type == "Supplier":
			self.query = "delivery_note_no"
			self.doctype = "Purchase Invoice"

	def setup_column(self):
		self.columns = [
			{"label": _("Date"), 			"fieldname": "posting_date", "fieldtype": "Date", "width": 120},
			{"label": _("Invoice"), 		"fieldname": "voucher_no",	 "fieldtype": "Link", "width": 200, "options":"Sales Invoice"},
		]

		if self.doctype == "Sales Invoice":
			self.columns +=[
				{"label": _("Customer PO"), 	"fieldname": "customer_po",	 "fieldtype": "Data", "width": 120 },
			]
		else:
			self.columns +=[
				{"label": _("Delivery Note"), 	"fieldname": "delivery_note","fieldtype": "Data", "width": 150 },
			]
			
		self.columns += [
			{"label": _("Amount"), 			"fieldname": "outstanding_amount",		 "fieldtype": "Currency", "width": 120},
		]

	def get_data(self):
		self.data = frappe.db.sql("""
			select 
				posting_date, 
				name as voucher_no,
				outstanding_amount,
				status,
				{query}
			from 
				`tab{doctype}` si
			where 
				si.docstatus = 1
				and si.outstanding_amount != 0 								
				{conditions}
		""".format(
			query=self.query,
			doctype=self.doctype,
			conditions=self.conditions
		), (self.filters), as_dict=1)

	def execute(self):
		if not self.validate_filters():
			return self.columns, self.data
		
		self.setup_query()
		self.setup_filters()
		self.setup_column()
		self.get_data()

		return self.columns, self.data