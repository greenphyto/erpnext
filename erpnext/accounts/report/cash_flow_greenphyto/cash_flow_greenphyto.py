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
	"Long Term Lease Liabilities":"270000 - Long Term Lease Liabilities - GPL"
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
	
	def get_sub_total(self, sub_title):
		return self.cf_data[""][sub_title]
	
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

# endregion
		
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


# 		# Gross Profit
# 		ref = self.get_row_reference("CF", "Revenue")
# 		ref2 = self.get_row_reference("CF", "COGS")
# 		self.loop_data("Gross Profit", lambda key: ref[key]-ref2[key])

# 		# Less: Operating Expenses
# 		self.loop_data("Less: Operating Expenses", lambda key: "")

# 		# Sales and Marketing Cost
# 		ref = self.get_row_reference("PL", ACCOUNT['Selling & Marketing'])
# 		self.loop_data("Sales and Marketing Cost", lambda key: ref[key])



# 		# Professional Fees
# 		ref = self.get_row_reference("PL", ACCOUNT["Professional Cost"])
# 		self.loop_data("Professional Fees", lambda key: ref[key])

# 		# Other Expenses
# 		ref = self.get_row_reference("PL", ACCOUNT["Expense Operating"])
# 		ref1 = self.get_row_reference("PL", ACCOUNT["Expense Other"])
# 		ref2 = self.get_row_reference("CF", "Sales and Marketing Cost")
# 		ref3 = self.get_row_reference("CF", "Manpower Cost")
# 		ref4 = self.get_row_reference("CF", "Professional Fees")
# 		self.loop_data("Other Expenses", lambda key: ref[key]+ref1[key]-ref2[key]-ref3[key]-ref4[key])

# 		# Operating Expenses
# 		self.loop_data("Operating Expenses", lambda key: sum([ 
# 			self.cf_data['Sales and Marketing Cost'][key],
# 			self.cf_data['Manpower Cost'][key],
# 			self.cf_data['Professional Fees'][key],
# 			self.cf_data['Other Expenses'][key],
# 		]))

# 		# Operating Profit/ (Loss)
# 		self.loop_data("Operating Profit/ (Loss)", lambda key: sum([ 
# 			self.cf_data['Gross Profit'][key],
# 			-1*self.cf_data['Operating Expenses'][key],
# 		]))

# 		# Depreciation
# 		ref = self.get_row_reference("PL", ACCOUNT["Depreciation"])
# 		self.loop_data("Depreciation", lambda key: ref[key])



# 		# EBITDA
# 		self.loop_data("EBITDA", lambda key: sum([ 
# 			self.cf_data['Operating Profit/ (Loss)'][key],
# 			self.cf_data['Depreciation'][key],
# 			self.cf_data['Interest'][key],
# 		]))



# 		# Other Income
# 		ref = self.get_row_reference("PL", ACCOUNT["Other Income"])
# 		self.loop_data("Other Income", lambda key: ref[key])

# 		# Net Profit/ (Loss)
# 		self.loop_data("EBITDA", lambda key: sum([ 
# 			self.cf_data['Operating Profit/ (Loss)'][key],
# 			self.cf_data['Other Income'][key],
# 		]))

# 		# Cash and Cash on hand
# 		ref = self.get_row_reference("BS", ACCOUNT["Cash in Bank"])
# 		self.loop_data("Cash and Cash on hand", lambda key: ref[key])


# 		# Accounts Receivables
# 		ref = self.get_row_reference("BS", ACCOUNT["Accounts Receivable"])
# 		self.loop_data("Accounts Receivables", lambda key: ref[key])

# 		# Deposits
# 		ref = self.get_row_reference("BS", ACCOUNT["Deposit"])
# 		self.loop_data("Deposits", lambda key: ref[key])

# 		# Other Receivables
# 		ref = self.get_row_reference("BS", ACCOUNT["Other Receivables"])
# 		self.loop_data("Other Receivables", lambda key: ref[key])

# 		# Non-Current Assets
# 		ref = self.get_row_reference("BS", ACCOUNT["Non Current Asset"])
# 		self.loop_data("Non-Current Assets", lambda key: ref[key])

# 		# Total Assets
# 		self.loop_data("Total Assets", lambda key: sum([ 
# 			self.cf_data['Cash and Cash on hand'][key],
# 			self.cf_data['Investments'][key],
# 			self.cf_data['Accounts Receivables'][key],
# 			self.cf_data['Deposits'][key],
# 			self.cf_data['Other Receivables'][key],
# 			self.cf_data['Non-Current Assets'][key],
# 		]))







	
