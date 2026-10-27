import frappe

"""
bench --site erp-prod execute erpnext.patches.gp.restrict_finance_reports_to_accounts_manager.execute
"""
def execute():
	restrict_finance_reports_to_accounts_manager()


def restrict_finance_reports_to_accounts_manager():
	"""Restrict access of all Accounts (finance) reports to 'Accounts Manager' role only.

	Removes all existing roles from each report and sets a single role:
	Accounts Manager.
	"""
	print("Restricting finance reports to 'Accounts Manager' only...")

	target_role = "Accounts Manager"

	reports = [
		"Account Balance",
		"Accounts Payable",
		"Accounts Payable Summary",
		"Accounts Receivable",
		"Accounts Receivable Summary",
		"Asset Depreciation Ledger",
		"Asset Depreciations and Balances",
		"Balance Sheet",
		"Balance Sheet Greenphyto",
		"Balance Sheet Malaysia",
		"Balance Sheet V2",
		"Bank Clearance Summary",
		"Bank Reconciliation Statement",
		"Billed Items To Be Received",
		"Budget Variance Report",
		"Cash Flow",
		"Cash Flow Greenphyto",
		"Consolidated Financial Statement",
		"Customer Ledger Summary",
		"Deferred Revenue and Expense",
		"Delivered Items To Be Billed",
		"Dimension-wise Accounts Balance Report",
		"General Ledger",
		"Gross and Net Profit Report",
		"Gross Profit",
		"GST Return Summary Report",
		"Inactive Sales Items",
		"Item-wise Purchase Register",
		"Item-wise Sales Register",
		"Journal Entry List",
		"Part Number",
		"Payment Ledger",
		"Payment Period Based On Invoice Date",
		"POS Register",
		"Profitability Analysis",
		"Profit and Loss Malaysia",
		"Profit and Loss Statement",
		"Purchase Invoice Trends",
		"Purchase Register",
		"Purchase Taxes",
		"Received Items To Be Billed",
		"Sales Invoice Trends",
		"Sales Partners Commission",
		"Sales Payment Summary",
		"Sales Register",
		"Sales Taxes",
		"Share Balance",
		"Share Ledger",
		"Statement of Account (Outstanding)",
		"Supplier Ledger Summary",
		"Tax Detail",
		"TDS Computation Summary",
		"TDS Payable Monthly",
		"Trade Creditors",
		"Trade Creditors Summary",
		"Trade Debtors",
		"Trade Debtors Summary",
		"Trial Balance",
		"Trial Balance for Party",
		"Trial Balance (Simple)",
	]

	updated_count = 0
	not_found = []

	for report_name in reports:
		if not frappe.db.exists("Report", report_name):
			not_found.append(report_name)
			continue

		report = frappe.get_doc("Report", report_name)
		report.set("roles", [])
		report.append("roles", {"role": target_role})
		report.save(ignore_permissions=True)

		updated_count += 1
		print(f"  Updated: {report_name} -> {target_role}")

	frappe.db.commit()

	print(f"\nTotal updated: {updated_count}")
	if not_found:
		print(f"Reports not found: {', '.join(not_found)}")
