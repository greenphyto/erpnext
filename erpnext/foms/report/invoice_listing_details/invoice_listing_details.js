// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Invoice Listing Details"] = {
	"filters": [
		{
			"fieldname":"start_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"options":""
		},
		{
			"fieldname":"end_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"options":"Today"
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options":"Customer"
		},
		{
			"fieldname":"sales_invoice",
			"label": __("Invoice No"),
			"fieldtype": "Link",
			"options":"Sales Invoice"
		},
		{
			"fieldname":"show_credit_note",
			"label": __("Show Credit Note"),
			"fieldtype": "Check",
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
