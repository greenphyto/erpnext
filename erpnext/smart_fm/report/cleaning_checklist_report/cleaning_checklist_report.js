// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Cleaning Checklist Report"] = {
	"filters": [
		{
			"fieldname": "month",
			"fieldtype": "Select",
			"label": "Month",
			"options":"\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember"
		},
		{
			"fieldname": "year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
		},
		{
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"label": "Date"
		},
		{
			"fieldname": "cleaned_by",
			"fieldtype": "Link",
			"label": "Cleaned by",
			"options":"User"
		},
		{
			"fieldname": "location",
			"fieldtype": "Select",
			"label": "Location",
			"options":"\nLevel 1\nLevel 2\nLevel 3\nLevel 4\nLevel 5"
		},
	]
};
