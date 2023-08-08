// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["To dos completion rate"] = {
	// filter from - to date
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": "Date From",
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": "Date To",
		},
	]
};
