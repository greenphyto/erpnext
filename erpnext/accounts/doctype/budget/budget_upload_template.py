# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Helper function to generate Budget Upload Template
"""

import frappe
from frappe import _


@frappe.whitelist()
def download_budget_template(company=None):
	"""
	Generate and download a sample Budget upload template in Excel format
	Format: Cost Center | Account | January | February | ... | December
	"""
	from frappe.utils.xlsxutils import make_xlsx
	
	# Month names
	months = [
		"January", "February", "March", "April", "May", "June",
		"July", "August", "September", "October", "November", "December"
	]
	
	# Build header row
	headers = [_("Cost Center"), _("Account")] + [_(month) for month in months]
	
	# Sample data
	data = [headers]  # First row is headers
	
	if company:
		# Get some sample expense accounts and cost centers for the company
		sample_cost_center = frappe.db.get_value(
			"Cost Center",
			filters={
				"company": company,
				"is_group": 0,
				"disabled": 0
			},
			pluck="name"
		) or "Main - " + company
		
		sample_accounts = frappe.db.get_all(
			"Account",
			filters={
				"company": company,
				"report_type": "Profit and Loss",
				"is_group": 0,
				"disabled": 0
			},
			fields=["name"],
			limit=3
		)
		
		for acc in sample_accounts:
			# Cost Center, Account, then 12 months with 0 values
			row = [sample_cost_center, acc.name] + [0] * 12
			data.append(row)
	else:
		# Generic sample
		data.append(["Main - Company", "Salary - Company"] + [0] * 12)
		data.append(["Main - Company", "Rent - Company"] + [0] * 12)
		data.append(["Operations - Company", "Utilities - Company"] + [0] * 12)
	
	# Generate Excel file
	xlsx_file = make_xlsx(data, "Budget Upload Template")
	
	frappe.response['filename'] = 'budget_upload_template.xlsx'
	frappe.response['filecontent'] = xlsx_file.getvalue()
	frappe.response['type'] = 'binary'
