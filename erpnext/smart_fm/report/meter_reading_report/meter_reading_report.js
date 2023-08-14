// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Meter Reading Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": "From Date",
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": "To Date",
		},
		{
			"fieldname": "group_by",
			"fieldtype": "Select",
			"label": "Group By",
			"options": "Utility\nType of Meter",
			"default": "Utility"
		},
		{
			"fieldname": "type_of_meter",
			"fieldtype": "Select",
			"label": "Type of Meter",
			"options": "Electricity\nWater\nGas",
			"default": "Electricity"
		},
		{
			"fieldname": "utility",
			"fieldtype": "Link",
			"label": "Utility",
			"options": "Utility"
		},
		{
			"fieldname": "meter_location",
			"fieldtype": "Link",
			"label": "Meter Location",
			"options": "Location",
		},
	]
};
