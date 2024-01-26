# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute as pl_report



def execute(filters=None):
	columns, data = [], []
	pl_data = get_pl_report_data(filters=filters)
	data = [pl_data]
	return columns, data


def get_pl_report_data(filters):
	pl_data = pl_report(filters)
	data = {}
	if len(pl_data) > 1 and pl_data[1]:
		for d in pl_data[1]:
			if d.get("account"):
				data[d['account']] = d

	return data