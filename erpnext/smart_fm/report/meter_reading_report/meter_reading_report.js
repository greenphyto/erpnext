// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Meter Reading Report"] = {
	"filters": [
		{
			"fieldname": "year",
			"fieldtype": "Link",
			"label": "Year",
			"options": "Fiscal Year"
		},
		{
			"fieldname": "group_by",
			"fieldtype": "Select",
			"label": "Group By",
			"options": "Utility\nType of Meter"
		},
		{
			"fieldname": "type_of_meter",
			"fieldtype": "Select",
			"label": "Type of Meter",
			"options": "\nElectricity\nWater\nGas",
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
