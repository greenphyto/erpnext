// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Work Order Profitability Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "work_order",
			label: __("Work Order"),
			fieldtype: "Link",
			options: "Work Order",
		},
		{
			fieldname: "item_code",
			label: __("Crop"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				return { filters: { is_stock_item: 1 } };
			},
		},
		{
			fieldname: "show_in_progress",
			label: __("Show In Progress Work Orders"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
