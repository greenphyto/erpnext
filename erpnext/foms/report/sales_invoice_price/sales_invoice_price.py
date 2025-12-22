# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from erpnext.foms.report.wip_account_detail.wip_account_detail import Report

def execute(filters=None):
	return Report(filters).execute()
