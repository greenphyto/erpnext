# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute as pl_report
from erpnext.accounts.report.balance_sheet_v2.balance_sheet_v2 import execute as bs_report
from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_period_list
)

def execute(filters=None):
	columns, data = [], []
	
	return CashFlowReport(filters).run()

ACCOUNT = {
	"Direct Income": "Direct Income - GPL",
	"COGS":"Cost of Goods Sold - GPL",
	"COS":"Cost of Sales - GPL",
	"Selling & Marketing": "600002 - Selling & Marketing - GPL - GPL",
	"Staff Cost": "600001 - Staff Cost - GPL",
	"Professional Cost": "600003 - Audit & Consultation Fees - GPL",
	"Expense Operating": "Expenses-Operating - GPL",
	"Expense Other": "Expenses-Other - GPL",
	"Depreciation": "Depreciation - GPL",
	"Finance Expense": "Finance Expenses - GPL",
	"Other Income": "Indirect Income - GPL",
	"Cash in Bank": "100030 - Cash in Bank - GPL",
	"Investments": "100090 - Investments - GPL",
	"Accounts Receivable": "100020 - Accounts Receivable - GPL",
	"Deposit": "100060 - Deposit & Prepayment - GPL",
	"Other Receivables": "147000 - GST Input Tax - GPL",
	"Non Current Asset": "100000 - Non-Current Assets - GPL"
}

# region

def get_pl_report_data(filters):
	pl_data = pl_report(filters)
	data = {}
	if len(pl_data) > 1 and pl_data[1]:
		for d in pl_data[1]:
			if d.get("account"):
				data[d['account']] = d

	return data

def get_bs_report_data(filters):
	bs_data = bs_report(filters)
	data = {}
	if len(bs_data) > 1 and bs_data[1]:
		for d in bs_data[1]:
			if d.get("account"):
				data[d['account']] = d

	return data

class CashFlowReport():
	def __init__(self, filters):
		self.filters = filters
		self.columns = []
		self.data = []

	def setup_report(self):
		self.period_list = get_period_list(
			self.filters.from_fiscal_year,
			self.filters.to_fiscal_year,
			self.filters.period_start_date,
			self.filters.period_end_date,
			self.filters.filter_based_on,
			self.filters.periodicity,
			company=self.filters.company,
			month=self.filters.month,
			to_month=self.filters.to_month,
		)
			
	def setup_column(self):
		self.columns = get_columns(
			self.filters.periodicity, self.period_list, self.filters.accumulated_values, self.filters.company
		)

	def get_data(self):
		self.data = []
		self.pl_data = get_pl_report_data(filters=self.filters)
	
		self.filters.accumulated_values = 1
		self.bs_data = get_bs_report_data(filters=self.filters)

		self.cf_data = {}
		self.data = [self.pl_data, self.bs_data, self.cf_data]

	def run(self):
		self.setup_report()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data
	
	def get_row_reference(self, source, account):
		if source == "PL":
			return self.pl_data.get(account) 
		elif source == "BS":
			return self.bs_data.get(account)
		elif source == "CF":
			return self.cf_data.get(account)

	def loop_data(self, account_title, func):
		data = {
			'account' : account_title
		}
		for period in self.period_list:
			key = period.key
			data[key] = func(key)

		self.cf_data[account_title] = data
		self.data.append(data)
		
		return data
	
	def process_data(self):
		# Revenue
		ref = self.get_row_reference("PL", ACCOUNT['Direct Income'])
		self.loop_data("Revenue", lambda key: ref[key])

		# COGS
		ref = self.get_row_reference("PL", ACCOUNT['COGS'])
		ref2 = self.get_row_reference("PL", ACCOUNT['COS'])
		self.loop_data("COGS", lambda key: ref[key]+ref2[key])

		# Gross Profit
		ref = self.get_row_reference("CF", "Revenue")
		ref2 = self.get_row_reference("CF", "COGS")
		self.loop_data("Gross Profit", lambda key: ref[key]-ref2[key])

		# Less: Operating Expenses
		self.loop_data("Less: Operating Expenses", lambda key: "")

		# Sales and Marketing Cost
		ref = self.get_row_reference("PL", ACCOUNT['Selling & Marketing'])
		self.loop_data("Sales and Marketing Cost", lambda key: ref[key])

		# Manpower Cost
		ref = self.get_row_reference("PL", ACCOUNT["Staff Cost"])
		self.loop_data("Manpower Cost", lambda key: ref[key])

		# Professional Fees
		ref = self.get_row_reference("PL", ACCOUNT["Professional Cost"])
		self.loop_data("Professional Fees", lambda key: ref[key])

		# Other Expenses
		ref = self.get_row_reference("PL", ACCOUNT["Expense Operating"])
		ref1 = self.get_row_reference("PL", ACCOUNT["Expense Other"])
		ref2 = self.get_row_reference("CF", "Sales and Marketing Cost")
		ref3 = self.get_row_reference("CF", "Manpower Cost")
		ref4 = self.get_row_reference("CF", "Professional Fees")
		self.loop_data("Other Expenses", lambda key: ref[key]+ref1[key]-ref2[key]-ref3[key]-ref4[key])

		# Operating Expenses
		self.loop_data("Operating Expenses", lambda key: sum([ 
			self.cf_data['Sales and Marketing Cost'][key],
			self.cf_data['Manpower Cost'][key],
			self.cf_data['Professional Fees'][key],
			self.cf_data['Other Expenses'][key],
		]))

		# Operating Profit/ (Loss)
		self.loop_data("Operating Profit/ (Loss)", lambda key: sum([ 
			self.cf_data['Gross Profit'][key],
			-1*self.cf_data['Operating Expenses'][key],
		]))

		# Depreciation
		ref = self.get_row_reference("PL", ACCOUNT["Depreciation"])
		self.loop_data("Depreciation", lambda key: ref[key])

		# Interest
		ref = self.get_row_reference("PL", ACCOUNT["Finance Expense"])
		self.loop_data("Interest", lambda key: ref[key])

		# EBITDA
		self.loop_data("EBITDA", lambda key: sum([ 
			self.cf_data['Operating Profit/ (Loss)'][key],
			self.cf_data['Depreciation'][key],
			self.cf_data['Interest'][key],
		]))

# endregion


		# Other Income
		ref = self.get_row_reference("PL", ACCOUNT["Other Income"])
		self.loop_data("Other Income", lambda key: ref[key])

		# Net Profit/ (Loss)
		self.loop_data("EBITDA", lambda key: sum([ 
			self.cf_data['Operating Profit/ (Loss)'][key],
			self.cf_data['Other Income'][key],
		]))

		# Cash and Cash on hand
		ref = self.get_row_reference("BS", ACCOUNT["Cash in Bank"])
		self.loop_data("Cash and Cash on hand", lambda key: ref[key])

		# Investments
		ref = self.get_row_reference("BS", ACCOUNT["Investments"])
		self.loop_data("Investments", lambda key: ref[key])

		# Accounts Receivables
		ref = self.get_row_reference("BS", ACCOUNT["Accounts Receivable"])
		self.loop_data("Accounts Receivables", lambda key: ref[key])

		# Deposits
		ref = self.get_row_reference("BS", ACCOUNT["Deposit"])
		self.loop_data("Deposits", lambda key: ref[key])

		# Other Receivables
		ref = self.get_row_reference("BS", ACCOUNT["Other Receivables"])
		self.loop_data("Other Receivables", lambda key: ref[key])

		# Non-Current Assets
		ref = self.get_row_reference("BS", ACCOUNT["Non Current Asset"])
		self.loop_data("Non-Current Assets", lambda key: ref[key])

		# Total Assets
		self.loop_data("Total Assets", lambda key: sum([ 
			self.cf_data['Cash and Cash on hand'][key],
			self.cf_data['Investments'][key],
			self.cf_data['Accounts Receivables'][key],
			self.cf_data['Deposits'][key],
			self.cf_data['Other Receivables'][key],
			self.cf_data['Non-Current Assets'][key],
		]))







	
