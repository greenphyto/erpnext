# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute as pl_report
from erpnext.accounts.report.balance_sheet_v2.balance_sheet_v2 import execute as bs_report
from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_period_list
)
from frappe.utils import get_first_day, add_months, add_years, get_last_day, getdate,add_days, cstr
from erpnext.accounts.utils import get_fiscal_year

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
	"Non Current Asset": "100000 - Non-Current Assets - GPL",
	"Repairs and Maintenance":"600004 - Repairs and Maintenance - GPL",
	"Operating Expense":"600005 - Operating Expense - GPL",
	"Subscription Fees":"600006 - Subscription Fees - GPL",
	"Foreign Exchange":"600007 - Other Operating Expenses - GPL",
	"Motor Vehicles":"110020 - Motor Vehicles - GPL",
	"Plant Machinery":"110030 - Plant & Machinery - GPL",
	"Furniture":"110050 - Furniture & Fittings - GPL",
	"IT Hardware":"110070 - IT (Hardware) - GPL",
	"IT Others":"110072 - IT (Others) - GPL",
	"Land":"110003 - Land - GPL",
	"Dep Motor Vehicles":"110520 - Acc Dep - Motor Vehicles - GPL",
	"Dep Plant Machinery":"110530 - Acc Dep - Plant & Machinery - GPL",
	"Dep Furniture":"110550 - Acc Dep - Furniture & Fittings - GPL",
	"Dep IT Hardware":"110570 - Acc Dep - IT ( Hardware) - GPL",
	"Dep IT Others":"110575 - Acc Dep - IT (Software) - GPL",
	"Dep Land":"110512 - Acc Dep - Land - GPL",
	"Asset U Construction":"110900 - Assets U. Construction - GPL",
	"Right-of-use asset":"Right-Of-Use Assets - GPL",
	"Acc Receivable":'100020 - Accounts Receivable - GPL',
	"Deposit and Prepayment":'100060 - Deposit & Prepayment - GPL',
	"GST Input":'100080 - GST- Input Tax - GPL',
	"Duties and Taxes":'240000 - Duties and Taxes - GPL',
	"Account Payable":'200009 - Account Payable - GPL',
	"Accruals and Provision":"210000 - Accruals and Provision - GPL",
	"Contra Account":"250000 - Contra Account - GPL",
	"Amount Due to Directors":"230000 - Amount Due to Directors - GPL",
	"Term loan liabilities":"220040 - ST - Term Loan Liabilities - GPL",
	"UOB 4m":"280030 - Bank Term Loan UOB $4m - GPL",
	"UOB 5m":"280040 - Bank Term Loan UOB $5m - GPL",
	"Hire Purchase Creditors":"220010 - ST - Hire Purchase Creditor - GPL",
	"Hire Purchase Interest":"220020 - ST - Hire Purchase Interest Payable - GPL",
	"Lease Liabilities":"220030 - ST - Lease Liabilities - GPL",
	"UOB LEFS":"280010 - UOB TL-LEFS (LN:8018611651) - GPL",
	"UOB TLC":"280020 - UOB Term Loan Construction - GPL",
	"UOB PFL":"280050 - UOB Premium Financing Loan - PFL (LN:8018088347) - GPL",
	"Other LT Liabilities":"260000 - Other LT Liabilities - GPL",
	"Long Term Lease Liabilities":"270000 - Long Term Lease Liabilities - GPL",
	"Retained Earnings":"340000 - Retained Earnings - GPL",
	"Current Year Profit / (Loss)":"'Profit / (Loss) for the Year'",
	"Ordinary Shares":"300000 - Shares Ordinary - GPL",
	"Preference Shares":'310000 - Shares Preference "A" - GPL',
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
		self.use_date = self.period_list[0]
			
	def setup_column(self):
		self.columns = get_columns(
			self.filters.periodicity, self.period_list, self.filters.accumulated_values, self.filters.company
		)

	def get_data(self):
		self.data = []
		self.cf_data_prev = {}
		self.pl_data = get_pl_report_data(filters=self.filters)
	
		self.filters.accumulated_values = 1
		self.bs_data = get_bs_report_data(filters=self.filters)

		self.get_previous_month()

		self.cf_data = {}
		self.data = [self.pl_data, self.bs_data, self.bs_data_prev, self.cf_data_prev]

	def get_previous_month(self):
		# previous month balance sheet
		prev_filters = frappe._dict(self.filters)

		if self.filters.filter_based_on == "Date Range":
			self.start_date = getdate(self.filters.period_start_date)
			if self.filters.periodicity in ['Single Month', 'Multi Month', 'Monthly']:
				months = 1
			elif self.filters.periodicity == 'Quarterly':
				months = 4
			elif self.filters.periodicity == 'Half-Yearly':
				months = 6
			else:
				months = 12
			prev_filters.period_start_date = add_months(self.filters.period_start_date, months*-1)
			prev_filters.period_end_date = add_months(self.filters.period_end_date, months*-1)
		else:
			prev_date = add_years(getdate("1-1-{}".format(self.use_date.from_date)), -1)
			self.end_date = getdate("31-12-{}".format(self.use_date.to_date))
			fy = get_fiscal_year(prev_date, as_dict=1)
			if fy:
				prev_filters.from_fiscal_year = fy.name
				prev_filters.to_fiscal_year = fy.name


		self.period_list_prev = get_period_list(
			prev_filters.from_fiscal_year,
			prev_filters.to_fiscal_year,
			prev_filters.period_start_date,
			prev_filters.period_end_date,
			prev_filters.filter_based_on,
			prev_filters.periodicity,
			company=prev_filters.company,
			month=prev_filters.month,
			to_month=prev_filters.to_month,
		)

		self.prev_key_date = self.period_list_prev[-1].key

		# self.start_from_previous =
		# self.end_from_previous = add_days(self.start_date, -1)
		# prev_filters.filter_based_on = "Date Range"
		# self.period_end_date = self.end_from_previous
		# self.period_start_date = self.start_from_previous

		self.bs_data_prev = get_bs_report_data(filters=prev_filters)
		# print(186, self.bs_data_prev)
		# self.last_bs_data_prev = self.bs_data_prev.get(self.prev_key_date)

		# Cash Flow
		self.get_previous_cashflow()

	def get_previous_cashflow(self):
		self.cf_data_prev = {}
		self.loop_data_prev("BALANCE SHEET", lambda key: "", is_group=1)
		self.loop_data_prev("Non-Current Assets", lambda key: "", is_group=1)

		# Property, Plant and Equipment
		ref = self.get_row_reference("BS Prev", ACCOUNT["Motor Vehicles"])
		ref1 = self.get_row_reference("BS Prev", ACCOUNT["Plant Machinery"])
		ref2 = self.get_row_reference("BS Prev", ACCOUNT["Furniture"])
		ref3 = self.get_row_reference("BS Prev", ACCOUNT["IT Hardware"])
		ref4 = self.get_row_reference("BS Prev", ACCOUNT["Dep Motor Vehicles"])
		ref5 = self.get_row_reference("BS Prev", ACCOUNT["Dep Plant Machinery"])
		ref6 = self.get_row_reference("BS Prev", ACCOUNT["Dep Furniture"])
		ref7 = self.get_row_reference("BS Prev", ACCOUNT["Dep IT Hardware"])
		self.loop_data_prev("Property, Plant and Equipment", lambda key: sum([ 
			 ref[key], ref1[key], ref2[key], ref3[key],
			ref4[key], ref5[key], ref6[key], ref7[key]
		]))

		# Intangible assets
		ref = self.get_row_reference("BS Prev", ACCOUNT["IT Others"])
		ref1 = self.get_row_reference("BS Prev", ACCOUNT["Dep IT Others"])
		self.loop_data_prev("Intangible Assets", lambda key: ref[key] + ref1[key])

		# Assets under Construction
		ref = self.get_row_reference("BS Prev", ACCOUNT["Asset U Construction"])
		self.loop_data_prev("Assets under Construction", lambda key: ref[key])

		# Right-of-use assets
		ref = self.get_row_reference("BS Prev", ACCOUNT["Land"])
		ref1 = self.get_row_reference("BS Prev", ACCOUNT["Dep Land"])
		ref2 = self.get_row_reference("BS Prev", ACCOUNT["Right-of-use asset"])
		self.loop_data_prev("Right-of-use Assets", lambda key: ref[key]+ref1[key]+ref2[key])

		self.loop_data_prev("", lambda key: sum([ 
			self.cf_data_prev['Property, Plant and Equipment'][key],
			self.cf_data_prev['Intangible Assets'][key],
			self.cf_data_prev['Assets under Construction'][key],
			self.cf_data_prev['Right-of-use Assets'][key],
		]), is_group=1, sub_title='Total non-current assets')

		self.loop_data_prev("", lambda key: "")

		# Trade & other receivables
		ref = self.get_row_reference("BS Prev", ACCOUNT["Acc Receivable"])
		ref1 = self.get_row_reference("BS Prev", ACCOUNT["Deposit and Prepayment"])
		ref2 = self.get_row_reference("BS Prev", ACCOUNT["GST Input"])
		ref3 = self.get_row_reference("BS Prev", ACCOUNT["Duties and Taxes"])
		self.loop_data_prev("Trade & other receivables", lambda key: ref[key]+ref1[key]+ref2[key]-ref3[key])

		# Cash and Cash equvalents
		ref = self.get_row_reference("BS Prev", ACCOUNT["Cash in Bank"])
		self.loop_data_prev("Cash and Cash equvalents", lambda key: ref[key])

		# Investments
		ref = self.get_row_reference("BS Prev", ACCOUNT["Investments"])
		self.loop_data_prev("Investments", lambda key: ref[key])

		self.loop_data_prev("", lambda key: sum([ 
			self.cf_data_prev['Trade & other receivables'][key],
			self.cf_data_prev['Cash and Cash equvalents'][key],
			self.cf_data_prev['Investments'][key],
		]), is_group=1, sub_title="Total current assets")

		self.loop_data_prev("", lambda key: "")

		# Total Assets
		ref=self.get_sub_total_prev("Total non-current assets")
		ref1=self.get_sub_total_prev("Total current assets")
		self.loop_data_prev("Total Assets", lambda key: sum([ 
			ref[key],
			ref1[key],
		]), is_group=1)

		self.loop_data_prev("", lambda key: "") 

		# Current liabilities
		self.loop_data_prev("Current liabilities", lambda key: "", is_group=1) 
		# Accounts Payable
		ref=self.get_row_reference("BS Prev", ACCOUNT["Account Payable"])
		ref1=self.get_row_reference("BS Prev", ACCOUNT["Accruals and Provision"])
		ref2=self.get_row_reference("BS Prev", ACCOUNT["Contra Account"])
		self.loop_data_prev("Accounts Payable", lambda key: ref[key]+ref1[key]+ref2[key])
		
		# Amount Due to Directors
		ref=self.get_row_reference("BS Prev", ACCOUNT["Amount Due to Directors"])
		self.loop_data_prev("Amount Due to Directors", lambda key: ref[key])

		# Term Loans
		ref=self.get_row_reference("BS Prev", ACCOUNT["Term loan liabilities"])
		ref1=self.get_row_reference("BS Prev", ACCOUNT["UOB 4m"])
		ref2=self.get_row_reference("BS Prev", ACCOUNT["UOB 5m"])
		self.loop_data_prev("Term Loans", lambda key: ref[key]+ref1[key]+ref2[key])

		# Lease Liabilities
		ref=self.get_row_reference("BS Prev", ACCOUNT["Hire Purchase Creditors"])
		ref1=self.get_row_reference("BS Prev", ACCOUNT["Hire Purchase Interest"])
		ref2=self.get_row_reference("BS Prev", ACCOUNT["Lease Liabilities"])
		self.loop_data_prev("Lease Liabilities", lambda key: ref[key]+ref1[key]+ref2[key])

		# Total Current Liabilities
		self.loop_data_prev("", lambda key: sum([ 
			self.cf_data_prev["Accounts Payable"][key],
			self.cf_data_prev["Amount Due to Directors"][key],
			self.cf_data_prev["Term Loans"][key],
			self.cf_data_prev["Lease Liabilities"][key],
		]), is_group=1, sub_title="total current liabilities")

		self.loop_data_prev("", lambda key: "")

		# Non-Current liabilities 
		self.loop_data_prev("Non-Current liabilities", lambda key: "", is_group=1)
		# Term Loans
		ref=self.get_row_reference("BS Prev", ACCOUNT["UOB LEFS"])
		ref1=self.get_row_reference("BS Prev", ACCOUNT["UOB TLC"])
		ref2=self.get_row_reference("BS Prev", ACCOUNT["UOB PFL"])
		self.loop_data_prev("Term Loans ", lambda key: ref[key]+ref1[key]+ref2[key])

		# Lease Liabilities
		ref=self.get_row_reference("BS Prev", ACCOUNT["Other LT Liabilities"])
		ref1=self.get_row_reference("BS Prev", ACCOUNT["Long Term Lease Liabilities"])
		self.loop_data_prev("Lease Liabilities ", lambda key: ref[key]+ref1[key])

		# Total Current Liabilities
		self.loop_data_prev("", lambda key: sum([ 
			self.cf_data_prev["Term Loans "][key],
			self.cf_data_prev["Lease Liabilities "][key],
		]), is_group=1, sub_title="total non-current liabilities")

		# Total liabilities
		ref=self.get_sub_total_prev("total current liabilities")
		ref1=self.get_sub_total_prev("total non-current liabilities")
		self.loop_data_prev("Total Liabilities", lambda key: sum([ 
			ref[key],
			ref1[key],
		]), is_group=1)

		# Equity
		self.loop_data_prev("Equity", lambda key: "", is_group=1)
		# Retained Earnings
		ref=self.get_row_reference("BS Prev", ACCOUNT["Retained Earnings"])
		self.loop_data_prev("Retained Earnings", lambda key: ref[key])
		# Current Year Profit / (Loss)
		ref=self.get_row_reference("BS Prev", ACCOUNT["Current Year Profit / (Loss)"])
		self.loop_data_prev("Current Year Profit / (Loss)", lambda key: ref[key])
		# Ordinary Shares
		ref=self.get_row_reference("BS Prev", ACCOUNT["Ordinary Shares"])
		self.loop_data_prev("Ordinary Shares", lambda key: ref[key])
		# Preference Shares
		ref=self.get_row_reference("BS Prev", ACCOUNT["Preference Shares"])
		self.loop_data_prev("Preference Shares", lambda key: ref[key])

		self.loop_data_prev("", lambda key: "")

		# Total Equity
		self.loop_data_prev("Total Equity", lambda key: sum([ 
			self.cf_data_prev["Retained Earnings"][key],
			self.cf_data_prev["Current Year Profit / (Loss)"][key],
			self.cf_data_prev["Ordinary Shares"][key],
			self.cf_data_prev["Preference Shares"][key],
		]), is_group=1)

		self.loop_data_prev("", lambda key: "")

		return self.cf_data_prev

	def run(self):
		self.setup_report()
		self.setup_column()
		self.get_data()
		self.process_data()

		return self.columns, self.data
	
	def get_row_reference(self, source, account):
		data = {}
		if source == "PL":
			data = self.pl_data.get(account) 
		elif source == "BS":
			data = self.bs_data.get(account)
		elif source == "CF":
			data = self.cf_data_prev.get(account)
		elif source == "BS Prev":
			data = self.bs_data_prev.get(account)
		
		def_data = {}
		def_data[self.prev_key_date] = 0
		return frappe._dict(data or def_data)

	def loop_data(self, account_title, func, is_group=False, sub_title=""):
		data = {
			'account' : account_title
		}
		for period in self.period_list:
			key = period.key
			data[key] = func(key)
		if is_group:
			data['is_group'] = 1

		if account_title:
			self.cf_data[account_title] = data
		else:
			if "" not in self.cf_data:
				self.cf_data[account_title] = {}
			
			self.cf_data[account_title][sub_title] = data

		self.data.append(data)
		
		return data

	def loop_data_prev(self, account_title, func, is_group=False, sub_title=""):
		data = {
			'account' : account_title
		}

		key = self.prev_key_date

		for d in [key]:	
			data[key] = func(key)

		if is_group:
			data['is_group'] = 1

		if account_title:
			self.cf_data_prev[account_title] = data
		else:
			if "" not in self.cf_data_prev:
				self.cf_data_prev[account_title] = {}
			
			self.cf_data_prev[account_title][sub_title] = data

		self.data.append(data)
		
		return data
	
	def get_sub_total(self, sub_title):
		return self.cf_data[""][sub_title]

	def get_sub_total_prev(self, sub_title):
		return self.cf_data_prev[""][sub_title]
	
	def get_prev_data(self, types, account):
		data = {}
		prev_key = None

		if types == "BS":
			prev_data = self.bs_data_prev.get(account)
		else:
			prev_data = self.cf_data_prev.get(account)
		
		if types == "BS":
			cur_data = self.bs_data.get(account)
		else:
			cur_data = self.cf_data.get(account)

		for d in self.period_list:
			if not prev_key:
				data[d.key] = prev_data[self.prev_key_date]
			else:
				data[d.key] = cur_data[prev_key]

			prev_key = d.key

		return data
	
	def process_data(self):

		self.loop_data("INCOME STATEMENT", lambda key: "", is_group=1)

		# Revenue
		ref = self.get_row_reference("PL", ACCOUNT['Direct Income'])
		self.loop_data("Revenue", lambda key: ref[key])

		# COGS
		ref = self.get_row_reference("PL", ACCOUNT['COGS'])
		ref2 = self.get_row_reference("PL", ACCOUNT['COS'])
		self.loop_data("COGS", lambda key: ref[key]+ref2[key])

		# Gross Profit
		self.loop_data("Gross Profit", lambda key: sum([ 
			self.cf_data['Revenue'][key],
			self.cf_data['COGS'][key],
		]), is_group=1)

		self.loop_data("", lambda key: "")

		# Other Income
		ref = self.get_row_reference("PL", ACCOUNT["Other Income"])
		self.loop_data("Other Income", lambda key: ref[key])

		self.loop_data("", lambda key: "")

		# Depreciation
		ref = self.get_row_reference("PL", ACCOUNT["Depreciation"])
		self.loop_data("Depreciation", lambda key: ref[key])

		# Manpower Cost
		ref = self.get_row_reference("PL", ACCOUNT["Staff Cost"])
		self.loop_data("Staff Cost", lambda key: ref[key])

		# Legal and Professional Fees
		ref = self.get_row_reference("PL", ACCOUNT["Professional Cost"])
		self.loop_data("Legal and Professional Fees", lambda key: ref[key])

		# Finance Cost
		ref = self.get_row_reference("PL", ACCOUNT["Finance Expense"])
		self.loop_data("Finance Cost", lambda key: ref[key])

		# Other operating expenses
		ref = self.get_row_reference("PL", ACCOUNT['Selling & Marketing'])
		ref1 = self.get_row_reference("PL", ACCOUNT["Repairs and Maintenance"])
		ref2 = self.get_row_reference("PL", ACCOUNT["Operating Expense"])
		ref3 = self.get_row_reference("PL", ACCOUNT["Subscription Fees"])
		self.loop_data("Other Operating Expenses", lambda key: ref[key]+ref1[key]+ref2[key]+ref3[key])

		# Foreign Exchange
		ref = self.get_row_reference("PL", ACCOUNT["Foreign Exchange"])
		self.loop_data("Foreign Exchange", lambda key: ref[key])

		self.loop_data("", lambda key: "")

		# Profit / (Loss) before tax
		self.loop_data("Profit / (Loss) before tax", lambda key: sum([ 
			self.cf_data['Gross Profit'][key],
			self.cf_data['Other Income'][key],
			-1*self.cf_data['Legal and Professional Fees'][key],
			-1*self.cf_data['Depreciation'][key],
			-1*self.cf_data['Finance Cost'][key],
			-1*self.cf_data['Staff Cost'][key],
			-1*self.cf_data['Other Operating Expenses'][key],
			-1*self.cf_data['Foreign Exchange'][key],
		]), is_group=1)

		self.loop_data("", lambda key: "")

		# Income Tax expenses
		self.loop_data("Income Tax Expenses", lambda key: 0)

		self.loop_data("", lambda key: "")

		# Net Profit/ (Loss) for the year
		self.loop_data("Net Profit/ (Loss) for the year", lambda key: sum([ 
			self.cf_data['Profit / (Loss) before tax'][key],
			-1*self.cf_data['Income Tax Expenses'][key],
		]), is_group=1)

		self.loop_data("", lambda key: "")
		self.loop_data("BALANCE SHEET", lambda key: "", is_group=1)
		self.loop_data("Non-Current Assets", lambda key: "", is_group=1)

		# Property, Plant and Equipment
		ref = self.get_row_reference("BS", ACCOUNT["Motor Vehicles"])
		ref1 = self.get_row_reference("BS", ACCOUNT["Plant Machinery"])
		ref2 = self.get_row_reference("BS", ACCOUNT["Furniture"])
		ref3 = self.get_row_reference("BS", ACCOUNT["IT Hardware"])
		ref4 = self.get_row_reference("BS", ACCOUNT["Dep Motor Vehicles"])
		ref5 = self.get_row_reference("BS", ACCOUNT["Dep Plant Machinery"])
		ref6 = self.get_row_reference("BS", ACCOUNT["Dep Furniture"])
		ref7 = self.get_row_reference("BS", ACCOUNT["Dep IT Hardware"])
		self.loop_data("Property, Plant and Equipment", lambda key: sum([ 
			 ref[key], ref1[key], ref2[key], ref3[key],
			ref4[key], ref5[key], ref6[key], ref7[key]
		]))

		# Intangible assets
		ref = self.get_row_reference("BS", ACCOUNT["IT Others"])
		ref1 = self.get_row_reference("BS", ACCOUNT["Dep IT Others"])
		self.loop_data("Intangible Assets", lambda key: ref[key] + ref1[key])

		# Assets under Construction
		ref = self.get_row_reference("BS", ACCOUNT["Asset U Construction"])
		self.loop_data("Assets under Construction", lambda key: ref[key])

		# Right-of-use assets
		ref = self.get_row_reference("BS", ACCOUNT["Land"])
		ref1 = self.get_row_reference("BS", ACCOUNT["Dep Land"])
		ref2 = self.get_row_reference("BS", ACCOUNT["Right-of-use asset"])
		self.loop_data("Right-of-use Assets", lambda key: ref[key]+ref1[key]+ref2[key])

		self.loop_data("", lambda key: sum([ 
			self.cf_data['Property, Plant and Equipment'][key],
			self.cf_data['Intangible Assets'][key],
			self.cf_data['Assets under Construction'][key],
			self.cf_data['Right-of-use Assets'][key],
		]), is_group=1, sub_title='Total non-current assets')

		self.loop_data("", lambda key: "")

		# Trade & other receivables
		ref = self.get_row_reference("BS", ACCOUNT["Acc Receivable"])
		ref1 = self.get_row_reference("BS", ACCOUNT["Deposit and Prepayment"])
		ref2 = self.get_row_reference("BS", ACCOUNT["GST Input"])
		ref3 = self.get_row_reference("BS", ACCOUNT["Duties and Taxes"])
		self.loop_data("Trade & other receivables", lambda key: ref[key]+ref1[key]+ref2[key]-ref3[key])

		# Cash and Cash equvalents
		ref = self.get_row_reference("BS", ACCOUNT["Cash in Bank"])
		self.loop_data("Cash and Cash equvalents", lambda key: ref[key])

		# Investments
		ref = self.get_row_reference("BS", ACCOUNT["Investments"])
		self.loop_data("Investments", lambda key: ref[key])

		self.loop_data("", lambda key: sum([ 
			self.cf_data['Trade & other receivables'][key],
			self.cf_data['Cash and Cash equvalents'][key],
			self.cf_data['Investments'][key],
		]), is_group=1, sub_title="Total current assets")

		self.loop_data("", lambda key: "")

		# Total Assets
		ref=self.get_sub_total("Total non-current assets")
		ref1=self.get_sub_total("Total current assets")
		self.loop_data("Total Assets", lambda key: sum([ 
			ref[key],
			ref1[key],
		]), is_group=1)

		self.loop_data("", lambda key: "") 

		# Current liabilities
		self.loop_data("Current liabilities", lambda key: "", is_group=1) 
		# Accounts Payable
		ref=self.get_row_reference("BS", ACCOUNT["Account Payable"])
		ref1=self.get_row_reference("BS", ACCOUNT["Accruals and Provision"])
		ref2=self.get_row_reference("BS", ACCOUNT["Contra Account"])
		self.loop_data("Accounts Payable", lambda key: ref[key]+ref1[key]+ref2[key])
		
		# Amount Due to Directors
		ref=self.get_row_reference("BS", ACCOUNT["Amount Due to Directors"])
		self.loop_data("Amount Due to Directors", lambda key: ref[key])

		# Term Loans
		ref=self.get_row_reference("BS", ACCOUNT["Term loan liabilities"])
		ref1=self.get_row_reference("BS", ACCOUNT["UOB 4m"])
		ref2=self.get_row_reference("BS", ACCOUNT["UOB 5m"])
		self.loop_data("Term Loans", lambda key: ref[key]+ref1[key]+ref2[key])

		# Lease Liabilities
		ref=self.get_row_reference("BS", ACCOUNT["Hire Purchase Creditors"])
		ref1=self.get_row_reference("BS", ACCOUNT["Hire Purchase Interest"])
		ref2=self.get_row_reference("BS", ACCOUNT["Lease Liabilities"])
		self.loop_data("Lease Liabilities", lambda key: ref[key]+ref1[key]+ref2[key])

		# Total Current Liabilities
		self.loop_data("", lambda key: sum([ 
			self.cf_data["Accounts Payable"][key],
			self.cf_data["Amount Due to Directors"][key],
			self.cf_data["Term Loans"][key],
			self.cf_data["Lease Liabilities"][key],
		]), is_group=1, sub_title="total current liabilities")

		self.loop_data("", lambda key: "")

		# Non-Current liabilities 
		self.loop_data("Non-Current liabilities", lambda key: "", is_group=1)
		# Term Loans
		ref=self.get_row_reference("BS", ACCOUNT["UOB LEFS"])
		ref1=self.get_row_reference("BS", ACCOUNT["UOB TLC"])
		ref2=self.get_row_reference("BS", ACCOUNT["UOB PFL"])
		self.loop_data("Term Loans ", lambda key: ref[key]+ref1[key]+ref2[key])

		# Lease Liabilities
		ref=self.get_row_reference("BS", ACCOUNT["Other LT Liabilities"])
		ref1=self.get_row_reference("BS", ACCOUNT["Long Term Lease Liabilities"])
		self.loop_data("Lease Liabilities ", lambda key: ref[key]+ref1[key])

		# Total Current Liabilities
		self.loop_data("", lambda key: sum([ 
			self.cf_data["Term Loans "][key],
			self.cf_data["Lease Liabilities "][key],
		]), is_group=1, sub_title="total non-current liabilities")

		# Total liabilities
		ref=self.get_sub_total("total current liabilities")
		ref1=self.get_sub_total("total non-current liabilities")
		self.loop_data("Total Liabilities", lambda key: sum([ 
			ref[key],
			ref1[key],
		]), is_group=1)

		# Equity
		self.loop_data("Equity", lambda key: "", is_group=1)
		# Retained Earnings
		ref=self.get_row_reference("BS", ACCOUNT["Retained Earnings"])
		self.loop_data("Retained Earnings", lambda key: ref[key])
		# Current Year Profit / (Loss)
		ref=self.get_row_reference("BS", ACCOUNT["Current Year Profit / (Loss)"])
		self.loop_data("Current Year Profit / (Loss)", lambda key: ref[key])
		# Ordinary Shares
		ref=self.get_row_reference("BS", ACCOUNT["Ordinary Shares"])
		self.loop_data("Ordinary Shares", lambda key: ref[key])
		# Preference Shares
		ref=self.get_row_reference("BS", ACCOUNT["Preference Shares"])
		self.loop_data("Preference Shares", lambda key: ref[key])

		self.loop_data("", lambda key: "")

		# Total Equity
		self.loop_data("Total Equity", lambda key: sum([ 
			self.cf_data["Retained Earnings"][key],
			self.cf_data["Current Year Profit / (Loss)"][key],
			self.cf_data["Ordinary Shares"][key],
			self.cf_data["Preference Shares"][key],
		]), is_group=1)

		self.loop_data("", lambda key: "")

		# CASHFLOW STATEMENT
		self.loop_data("CASHFLOW STATEMENT", lambda key: "", is_group=1)
		self.loop_data("", lambda key: "")
		# Cashflow from Operating activities
		self.loop_data("Cashflow from Operating activities", lambda key: "", is_group=1)
		# Loss before tax
		self.loop_data("Loss before tax", lambda key: self.cf_data["Current Year Profit / (Loss)"][key])
		# Adjustment for:-
		self.loop_data("Adjustment for:-", lambda key: 0)
		# Depreciation of plant and machinery
		self.loop_data("Depreciation of plant and machinery", lambda key: self.cf_data["Depreciation"][key])
		# Loss on valuation of investments
		self.loop_data("Loss on valuation of investments", lambda key: 0)
		# Interest Paid
		self.loop_data("Interest Paid", lambda key: self.cf_data["Finance Cost"][key])
		# Loss on disposal of investments
		self.loop_data("Loss on disposal of investments", lambda key: 0)
		# Operating cash flows before changes in working capital 
		self.loop_data("", lambda key: "")
		self.loop_data("Operating cash flows before changes in working capital", lambda key: sum([
			self.cf_data['Loss before tax'][key],
			self.cf_data["Adjustment for:-"][key],
			self.cf_data["Depreciation of plant and machinery"][key],
			self.cf_data["Loss on valuation of investments"][key],
			self.cf_data["Interest Paid"][key],
			self.cf_data["Loss on disposal of investments"][key],
		]), is_group=1)

		# Change in Working Capital 
		self.loop_data("", lambda key: "")
		self.loop_data("Change in Working Capital ", lambda key: "", is_group=1)
		# Decrease/(increase) in trade and other Receivables
		ref=self.get_prev_data("CF","Trade & other receivables")
		ref1=self.cf_data.get("Trade & other receivables")
		self.loop_data("Decrease/(increase) in trade and other Receivables", lambda key: ref[key]-ref1[key] )
		# Increase/(Decrease) in trade and other payables and accruals
		ref=self.cf_data.get("Accounts Payable")
		ref1=self.get_prev_data("CF","Accounts Payable")
		self.loop_data("Increase/(Decrease) in trade and other payables and accruals", lambda key: ref[key]-ref1[key])

		self.loop_data("", lambda key: "")
		# Cash flows used in operating activities
		self.loop_data("Cash flows used in operating activities", lambda key: sum([
			self.cf_data['Decrease/(increase) in trade and other Receivables'][key],
			self.cf_data["Increase/(Decrease) in trade and other payables and accruals"][key],
			self.cf_data["Operating cash flows before changes in working capital"][key],
		]), is_group=1)
		# Interest Paid
		self.loop_data("Interest Paid ", lambda key: -1*self.cf_data["Interest Paid"][key])
		# Net cash flows used in operating activities
		self.loop_data("", lambda key: "")
		self.loop_data("Net cash flows used in operating activities", lambda key: sum([
			self.cf_data["Cash flows used in operating activities"][key],
			self.cf_data["Interest Paid "][key],
		]), is_group=1)

		# Cash flows from investing activities
		self.loop_data("", lambda key: "")
		self.loop_data("Cash flows from investing activities", lambda key: "", is_group=1)

		# Purchase of plant and equipment
		ref=self.get_prev_data("CF","Property, Plant and Equipment")
		ref1=self.get_prev_data("CF","Intangible Assets")
		ref2=self.get_prev_data("CF","Assets under Construction")
		ref3=self.get_prev_data("CF","Right-of-use Assets")
		ref4=self.cf_data.get("Property, Plant and Equipment")
		ref5=self.cf_data.get("Intangible Assets")
		ref6=self.cf_data.get("Assets under Construction")
		ref7=self.cf_data.get("Right-of-use Assets")
		ref8=self.cf_data.get("Depreciation of plant and machinery")
		self.loop_data("Purchase of plant and equipment", lambda key: sum([
			ref[key],ref1[key],ref2[key],ref3[key],
			-ref4[key],-ref5[key],-ref6[key],-ref7[key],-ref8[key]
		]))

		# Purchase of intangible assets
		self.loop_data("Purchase of intangible assets", lambda key: 0)
		# Proceeds from investments
		ref=self.get_prev_data("CF", "Investments")
		ref1=self.cf_data['Investments']
		self.loop_data("Proceeds from investments", lambda key: ref[key]-ref1[key])
		# Net cash flows generated from/(used in) investing activities
		self.loop_data("Net cash flows generated from/(used in) investing activities", lambda key: sum([
			self.cf_data['Purchase of intangible assets'][key],
			self.cf_data['Proceeds from investments'][key],
			self.cf_data['Purchase of plant and equipment'][key],
		]), is_group=1)
		
		self.loop_data("", lambda key: "")
		# Cash flow from financing activities
		self.loop_data("Cash flow from financing activities", lambda key: "", is_group=1)

		# Proceed from issue of preference shares
		self.loop_data("Proceed from issue of preference shares", lambda key: 0)

		# (Repayment) from Term Loans
		ref=self.cf_data['Term Loans']
		ref1=self.get_prev_data("CF", "Term Loans")
		self.loop_data("(Repayment) from Term Loans", lambda key: ref[key]-ref1[key])

		# Drawdown from Term Loans
		ref=self.cf_data['Term Loans ']
		ref1=self.get_prev_data("CF", "Term Loans ")
		self.loop_data("Drawdown from Term Loans", lambda key: ref[key]-ref1[key])

		# Increase/(Decrease) in Amounts Due to Directors
		ref=self.cf_data['Amount Due to Directors']
		ref1=self.get_prev_data("CF", "Amount Due to Directors")
		self.loop_data("Increase/(Decrease) in Amounts Due to Directors", lambda key: ref[key]-ref1[key])

		# Increase/(Decrease) of lease liabilities
		ref=self.cf_data.get("Lease Liabilities")
		ref1=self.cf_data.get("Lease Liabilities ")
		ref2=self.get_prev_data("CF","Lease Liabilities")
		ref3=self.get_prev_data("CF","Lease Liabilities ")
		self.loop_data("Increase/(Decrease) of lease liabilities", lambda key: ref[key]+ref1[key]-ref2[key]-ref3[key])

		self.loop_data("", lambda key: "")
		# Net cash flows (used in)/generated from financing activities
		self.loop_data("Net cash flows (used in)/generated from financing activities", lambda key: sum([
			self.cf_data["(Repayment) from Term Loans"][key],
			self.cf_data["Drawdown from Term Loans"][key],
			self.cf_data["Increase/(Decrease) in Amounts Due to Directors"][key],
			self.cf_data["Increase/(Decrease) of lease liabilities"][key],
		]), is_group=1)

		self.loop_data("", lambda key: "")
		# Net Cashflow for the period
		self.loop_data("Net Cashflow for the period", lambda key: sum([
			self.cf_data["Net cash flows used in operating activities"][key],
			self.cf_data["Net cash flows generated from/(used in) investing activities"][key],
			self.cf_data["Net cash flows (used in)/generated from financing activities"][key],
		]), is_group=1)

		self.loop_data("", lambda key: "")
		# Beginning Balance
		# Ending Balance

