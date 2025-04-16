// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Distribution by Stores"] = {
	"filters": [
		{
			"fieldname":"start_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"options":""
		},
		{
			"fieldname":"end_date",
			"label": __("End Dtae"),
			"fieldtype": "Date",
			"options":""
		},
	],
	"onload": function(report) {
		const today = frappe.datetime.get_today();
		const startOfMonth = frappe.datetime.month_start(today);
		const endOfMonth = frappe.datetime.month_end(today);

		frappe.query_report.set_filter_value("start_date", startOfMonth);
		frappe.query_report.set_filter_value("end_date", endOfMonth);
	}
};
