# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute as pl_report
from erpnext.accounts.report.balance_sheet_v2.balance_sheet_v2 import execute as bs_report


def execute(filters=None):
	columns, data = [], []
	pl_data = get_pl_report_data(filters=filters)
	
	filters.accumulated_values = 1
	bs_data = get_bs_report_data(filters=filters)
	data = [bs_data]
	return columns, data


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