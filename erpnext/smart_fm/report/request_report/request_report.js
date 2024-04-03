// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Request Report"] = {
	"filters": [
		{
			"default": "All",
			"fieldname": "request_type",
			"fieldtype": "Select",
			"label": "Request Type",
			"options": [
				"All",
				"Maintenance Request",
				"Access Request",
				"Inspection Checklist",
				"Vendor Registration",
				"Key Control",
				"Work Order"
			],
			"reqd": 1
		},
		{
			"fieldname": "date_from",
			"fieldtype": "Date",
			"label": "Date From",
		},
		{
			"fieldname": "date_to",
			"fieldtype": "Date",
			"label": "Date To",
		},
	]
};
