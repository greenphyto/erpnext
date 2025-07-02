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
			"fieldname":"income_account",
			"label": __("Income Account"),
			"fieldtype": "Link",
			"options":"Account",
			"reqd":1
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
		{
			"fieldname":"show_missing_invoice",
			"label": __("Show Missing Invoice"),
			"fieldtype": "Check",
			"options":""
		}
	],
	"onload": function(report) {
		const today = frappe.datetime.get_today();
		const startOfMonth = frappe.datetime.month_start(today);
		const endOfMonth = frappe.datetime.month_end(today);

		frappe.query_report.set_filter_value("start_date", startOfMonth);
		frappe.query_report.set_filter_value("end_date", endOfMonth);

		frappe.db.get_value('Company', frappe.defaults.get_default('company'), 'default_income_account')
		.then(r => {
			if (r && r.message) {
				frappe.query_report.set_filter_value("income_account", r.message.default_income_account);
			}}
		)

	}
};
