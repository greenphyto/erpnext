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
		pl_data = get_pl_report_data(filters=self.filters)
	
		self.filters.accumulated_values = 1
		bs_data = get_bs_report_data(filters=self.filters)
		self.data = [bs_data]

	def run(self):
		self.setup_report()
		self.setup_column()
		self.get_data()

		return self.columns, self.data

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