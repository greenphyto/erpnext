# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe

from erpnext.accounts.report.trade_debtors.trade_debtors import DebtorCreditorReport

def execute(filters=None):
	args = {
		"party_type": "Supplier",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	return DebtorCreditorReport(filters).run(args)
