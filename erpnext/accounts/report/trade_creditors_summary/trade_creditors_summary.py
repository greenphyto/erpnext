# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe

from erpnext.accounts.report.trade_debtors_summary.trade_debtors_summary import (
	TradeCreditorsSummary,
)
def execute(filters=None):
	args = {
		"party_type": "Supplier",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	 

	return TradeCreditorsSummary(filters).run(args)


 