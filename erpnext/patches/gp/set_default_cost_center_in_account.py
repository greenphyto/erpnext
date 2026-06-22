import frappe
from frappe.utils import cint

def execute():
	set_default_cost_center_in_account()


def set_default_cost_center_in_account():
	"""Set default cost center in Account based on predefined mapping.

	This patch maps specific accounts to their corresponding cost centers
	for company GPL (and potentially other companies based on suffix).
	"""
	print("Setting default cost center in Account...")

	# Mapping: [account_number_with_name, cost_center_name]
	account_cost_center_map = [
		# --- Kategori: Accumulated Depreciation - GPL ---
		["110510 - Acc Dep - Property - GPL", "1020 - Finance - GPL"],
		["110512 - Acc Dep - Land - GPL", "1020 - Finance - GPL"],
		["110513 - Acc Dep - M & E System - GPL", "1020 - Finance - GPL"],
		["110520 - Acc Dep - Motor Vehicles - GPL", "1020 - Finance - GPL"],
		["110528 - Acc Dep - Plant & Machinery (Building) - GPL", "1020 - Finance - GPL"],
		["110530 - Acc Dep - Plant & Machinery (Production) - GPL", "1020 - Finance - GPL"],
		["110540 - Acc Dep - Renovations - GPL", "1020 - Finance - GPL"],
		["110550 - Acc Dep - Furniture & Fittings - GPL", "1020 - Finance - GPL"],
		["110560 - Acc Dep - Office Equipment - GPL", "1020 - Finance - GPL"],
		["110570 - Acc Dep - IT ( Hardware) - GPL", "1020 - Finance - GPL"],
		["110575 - Acc Dep - IT (Software) - GPL", "1020 - Finance - GPL"],

		# --- Kategori: Expenses-Other - Depreciation - GPL ---
		["690020 - Depreciation - Leasehold Land - GPL", "1020 - Finance - GPL"],
		["690030 - Depreciation - M & E System - GPL", "1020 - Finance - GPL"],
		["690040 - Depreciation - Building & Property - GPL", "1020 - Finance - GPL"],
		["690050 - Depreciation - Motor Vehicles - GPL", "1020 - Finance - GPL"],
		["690058 - Depreciation - Plant & Machinery (Building) - GPL", "1020 - Finance - GPL"],
		["690060 - Depreciation - Plant & Machinery (Production) - GPL", "1020 - Finance - GPL"],
		["690070 - Depreciation - Warehouse Equipment - GPL", "1020 - Finance - GPL"],
		["690080 - Depreciation - Production Equipment - GPL", "1020 - Finance - GPL"],
		["690100 - Depreciation - Renovation - GPL", "1020 - Finance - GPL"],
		["690110 - Depreciation - Furniture & Fittings - GPL", "1020 - Finance - GPL"],
		["690120 - Depreciation - Office Equipment - GPL", "1020 - Finance - GPL"],
		["690130 - Depreciation - IT (Hardware & Software) - GPL", "1020 - Finance - GPL"],

		# --- Sales Income - GPL ---
		["410010 - FOMS System - GPL", "1040 - Sales - GPL"],
		["410020 - Sales Income - GPL", "1040 - Sales - GPL"],
		["410030 - Sales Tooling - GPL", "1040 - Sales - GPL"],
		["410040 - Sales Services - GPL", "1040 - Sales - GPL"],
		["410050 - Sales - Others - GPL", "1040 - Sales - GPL"],
		["450000 - Discount Allowed - GPL", "1040 - Sales - GPL"],

		# --- Specific Accounts - GPL ---
		["620900 - Education & Training - GPL", "1030 - HR - GPL"],
		["830600 - UOB - Premium Financing Interest - GPL", "1020 - Finance - GPL"],
		["621800 - Advertising & Recruitment - GPL", "1030 - HR - GPL"],
		["650400 - Insurance - General - GPL", "1080 - Infrastructure & Maintenance - GPL"],
		["800700 - Government Grants - GPL", "1020 - Finance - GPL"],
		["650100 - Water & Utilities - GPL", "2020 - Production-WH - GPL"],

		# --- New from Excel v2/v3 (consistent across all voucher types) ---
		["500002 - COGS - Replacement Cost - GPL", "2020 - Production-WH - GPL"],
		["622005 - Production Sample - GPL", "2020 - Production-WH - GPL"],
		["650220 - Rental-Premises - GPL", "5010 - System - GPL"],
		["660200 - Car Parking - GPL", "5010 - System - GPL"],
		["670000 - Travelling & Accomodation - GPL", "1090 - CEO Office - GPL"],
		["670200 - Meeting Expenses - GPL", "1090 - CEO Office - GPL"],
		["700100 - Realised FX Gain/Loss - GPL", "2020 - Production-WH - GPL"],
		["800500 - Miscellaneous Income - GPL", "1040 - Sales - GPL"],
		["800600 - Export Electricity Income - GPL", "1040 - Sales - GPL"],

		# --- Skipped (conflicting cost_center per voucher type) ---
		# 680000 - Legal & Professional Fees: JE->1080, PI->5010
		# 800710 - Amortisation Deferred Income: v2->1040, v3->1020 (conflicting)
	]

	updated_count = 0
	not_found_accounts = []
	not_found_cost_centers = []

	for account_full, cost_center_name in account_cost_center_map:
		# Extract account_number from "110510 - Acc Dep - Property - GPL"
		account_number = account_full.split(" - ")[0]

		# Extract company suffix from cost_center_name (e.g., "GPL" from "1020 - Finance - GPL")
		company = cost_center_name.split(" - ")[-1]

		# Find Account by account_number and company
		account_name = frappe.db.get_value(
			"Account",
			account_full,
			"name",
		)

		if not account_name:
			not_found_accounts.append(f"{account_number} ({company})")
			continue

		# Find Cost Center by name and company
		cost_center = frappe.db.get_value(
			"Cost Center",
			cost_center_name,
			"name",
		)

		if not cost_center:
			not_found_cost_centers.append(f"{cost_center_name} ({company})")
			continue

		# Update cost_center in Account
		frappe.db.set_value("Account", account_name, "cost_center", cost_center)
		updated_count += 1
		print(f"  Updated: {account_name} -> {cost_center}")

	frappe.db.commit()

	print(f"\nTotal updated: {updated_count}")
	if not_found_accounts:
		print(f"Accounts not found: {', '.join(not_found_accounts)}")
	if not_found_cost_centers:
		print(f"Cost Centers not found: {', '.join(not_found_cost_centers)}")