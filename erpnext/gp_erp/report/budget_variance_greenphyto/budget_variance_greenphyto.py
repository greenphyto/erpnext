# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import datetime
import frappe
from frappe.utils import formatdate

# Import all functions from standard budget variance report
from erpnext.accounts.report.budget_variance_report.budget_variance_report import (
	execute as base_execute,
	get_columns as base_get_columns,
	get_chart_data as base_get_chart_data,
	get_fiscal_years,
)
from erpnext.controllers.trends import get_period_date_ranges, get_period_month_ranges


def execute(filters=None):
	"""
	Extended Budget Variance Report with YTD (Year-To-Date) filtering.
	Shows one Budget YTD column (full year) and Actual columns up to current date.
	"""
	chart = None
	if not filters:
		filters = {}
	
	# Call base execute but with YTD-filtered period ranges
	from erpnext.accounts.report.budget_variance_report.budget_variance_report import (
		get_cost_centers,
		get_dimension_account_month_map,
		get_dimension_target_details,
	)
	
	columns = get_columns_ytd(filters)
	if filters.get("budget_against_filter"):
		dimensions = filters.get("budget_against_filter")
	else:
		dimensions = get_cost_centers(filters)

	# Get period ranges and filter to YTD
	period_month_ranges = get_period_month_ranges(filters["period"], filters["from_fiscal_year"])
	period_month_ranges = filter_periods_ytd(period_month_ranges, filters)
	
	cam_map = get_dimension_account_month_map(filters)
	
	# Get budget totals (full year)
	budget_totals = get_budget_totals(filters)

	data = []
	for dimension in dimensions:
		dimension_items = cam_map.get(dimension)
		if dimension_items:
			data = get_final_data_ytd(dimension, dimension_items, filters, period_month_ranges, data, budget_totals)

	# Enable chart with Actual (bar) and Budget YTD (line)
	# chart = get_chart_data_ytd(filters, columns, data)

	return columns, data, None, chart


def get_budget_totals(filters):
	"""Get total budget for full year (all 12 months)"""
	from erpnext.accounts.report.budget_variance_report.budget_variance_report import (
		get_dimension_target_details,
	)
	
	dimension_target_details = get_dimension_target_details(filters)
	budget_totals = {}
	
	for ccd in dimension_target_details:
		key = (ccd.budget_against, ccd.account)
		if key not in budget_totals:
			budget_totals[key] = 0
		budget_totals[key] += ccd.budget_amount
	
	return budget_totals


def get_account_code_and_name(account):
	"""Split account into code and name. Format: 'Code - Name' """
	if " - " in account:
		parts = account.split(" - ", 1)
		return parts[0].strip(), parts[1].strip()
	else:
		# If no separator, try to get from database
		account_info = frappe.db.get_value("Account", account, ["account_number", "account_name"], as_dict=True)
		if account_info:
			return account_info.account_number or "", account_info.account_name or account
		return "", account


def get_final_data_ytd(dimension, dimension_items, filters, period_month_ranges, data, budget_totals):
	"""Get final data with Budget YTD and Actual columns only"""
	from frappe.utils import flt
	from erpnext.accounts.report.budget_variance_report.budget_variance_report import get_fiscal_years
	
	for account, monthwise_data in dimension_items.items():
		# Split account into code and name
		account_code, account_name = get_account_code_and_name(account)
		row = [dimension, account_code, account_name]
		
		total_actual = 0
		for year in get_fiscal_years(filters):
			for relevant_months in period_month_ranges:
				period_actual = 0
				for month in relevant_months:
					if monthwise_data.get(year[0]):
						month_data = monthwise_data.get(year[0]).get(month, {})
						actual_value = flt(month_data.get("actual", 0))
						period_actual += actual_value
						total_actual += actual_value
				
				row.append(period_actual)
		
		# Add total actual if not yearly
		if filters["period"] != "Yearly":
			row.append(total_actual)
		
		# Add Budget YTD column (total for full year)
		budget_ytd = budget_totals.get((dimension, account), 0)
		row.append(budget_ytd)
		
		# Calculate Variance $ = Total Actual - Budget YTD
		variance_amount = total_actual - budget_ytd
		row.append(variance_amount)
		
		# Calculate Variance % = (Variance $ / Budget YTD) × 100
		if budget_ytd != 0:
			variance_percent = (variance_amount / budget_ytd) * 100
		else:
			variance_percent = 0
		row.append(variance_percent)
		
		data.append(row)

	return data


def filter_periods_ytd(period_month_ranges, filters):
	"""Filter period ranges to only include periods up to current date (YTD)"""
	current_date = datetime.date.today()
	current_month = current_date.strftime("%B")
	
	# Get list of months up to current month
	months_order = ["January", "February", "March", "April", "May", "June",
					"July", "August", "September", "October", "November", "December"]
	current_month_index = months_order.index(current_month)
	valid_months = set(months_order[:current_month_index + 1])
	
	filtered_ranges = []
	for month_range in period_month_ranges:
		# Check if any month in this range is valid (up to current month)
		if any(month in valid_months for month in month_range):
			# Filter the months within this range to only include valid months
			filtered_months = [month for month in month_range if month in valid_months]
			if filtered_months:
				filtered_ranges.append(filtered_months)
	
	return filtered_ranges


def get_columns_ytd(filters):
	"""Get columns: Budget YTD (one column) and Actual columns up to current date (YTD)"""
	from frappe import _
	
	columns = [
		{
			"label": _(filters.get("budget_against")),
			"fieldtype": "Link",
			"fieldname": "budget_against",
			"options": filters.get("budget_against"),
			"width": 150,
		},
		{
			"label": _("Account Code"),
			"fieldname": "account_code",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Description"),
			"fieldname": "account_name",
			"fieldtype": "Data",
			"width": 200,
		}
	]

	group_months = False if filters["period"] == "Monthly" else True
	fiscal_year = get_fiscal_years(filters)
	current_date = datetime.date.today()

	# Add Actual columns only (up to current date)
	for year in fiscal_year:
		for from_date, to_date in get_period_date_ranges(filters["period"], year[0]):
			# Only show columns up to current date (YTD)
			if from_date > current_date:
				continue
			
			if filters["period"] == "Yearly":
				label = _("Actual") + " " + str(year[0])
				columns.append(
					{"label": label, "fieldtype": "Float", "fieldname": frappe.scrub(label), "width": 150}
				)
			else:
				label = _("Actual") + " (%s)" + " " + str(year[0])
				if group_months:
					label = label % (
						formatdate(from_date, format_string="MMM") + "-" + formatdate(to_date, format_string="MMM")
					)
				else:
					label = label % formatdate(from_date, format_string="MMM")

				columns.append(
					{"label": label, "fieldtype": "Float", "fieldname": frappe.scrub(label), "width": 150}
				)
	

	# Add Total Actual column if not yearly
	if filters["period"] != "Yearly":
		columns.append(
			{"label": _("Total Actual"), "fieldtype": "Float", "fieldname": "total_actual", "width": 150}
		)

	columns.append({
		"label": _("Budget YTD"),
		"fieldtype": "Float",
		"fieldname": "budget_ytd",
		"width": 150,
	})
	
	# Add Variance columns
	columns.append({
		"label": _("Variance $"),
		"fieldtype": "Float",
		"fieldname": "variance_amount",
		"width": 150,
	})
	
	columns.append({
		"label": _("Variance %"),
		"fieldtype": "Percent",
		"fieldname": "variance_percent",
		"width": 150,
	})

	return columns


def get_chart_data_ytd(filters, columns, data):
	"""Get chart data: Actual (bar chart) and Budget YTD (line chart)"""
	from frappe import _
	from frappe.utils import flt
	
	if not data:
		return None

	labels = []
	fiscal_year = get_fiscal_years(filters)
	group_months = False if filters["period"] == "Monthly" else True
	current_date = datetime.date.today()

	# Build labels for periods (YTD)
	for year in fiscal_year:
		for from_date, to_date in get_period_date_ranges(filters["period"], year[0]):
			# Only show chart data up to current date (YTD)
			if from_date > current_date:
				continue
				
			if filters["period"] == "Yearly":
				labels.append(year[0])
			else:
				if group_months:
					label = (
						formatdate(from_date, format_string="MMM") + "-" + formatdate(to_date, format_string="MMM")
					)
					labels.append(label)
				else:
					label = formatdate(from_date, format_string="MMM")
					labels.append(label)

	no_of_periods = len(labels)
	
	# Initialize arrays for totals
	actual_values = [0] * no_of_periods
	total_budget_ytd = 0
	
	# Calculate totals per column
	for row in data:
		# Row structure: [dimension, account_code, account_name, actual1, actual2, ..., total_actual (optional), budget_ytd, variance$, variance%]
		# Start from index 3 (skip dimension, account_code, and account_name)
		for i in range(no_of_periods):
			actual_values[i] += flt(row[3 + i])
		
		# Get budget YTD from appropriate index
		# If period is not Yearly, there's a Total Actual column before Budget YTD
		if filters["period"] != "Yearly":
			budget_ytd_index = 3 + no_of_periods + 1  # +1 for Total Actual column
		else:
			budget_ytd_index = 3 + no_of_periods
		
		if budget_ytd_index < len(row):
			total_budget_ytd += flt(row[budget_ytd_index])
	
	# Budget YTD line (same value across all periods)
	budget_ytd_values = [total_budget_ytd] * no_of_periods

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Budget YTD"), "chartType": "line", "values": budget_ytd_values},
				{"name": _("Actual"), "chartType": "bar", "values": actual_values},
			],
		},
		"type": "axis-mixed",
		"fieldtype": "Currency",
	}
