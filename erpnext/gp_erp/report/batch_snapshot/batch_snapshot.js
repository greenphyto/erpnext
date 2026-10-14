// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Batch Snapshot"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
			on_change: function (report) {
				const company = report.get_filter_value("company");
				if (!company) {
					return;
				}
				frappe.db.get_value("Company", company, "default_warehouse_for_delivery", (r) => {
					if (r && r.default_warehouse_for_delivery) {
						report.set_filter_value("warehouse", r.default_warehouse_for_delivery);
					}
				});
			},
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			reqd: 1,
			get_query: function () {
				const company = frappe.query_report.get_filter_value("company");
				return { filters: { company: company } };
			},
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				return { filters: { is_stock_item: 1 } };
			},
		},
	],

	onload: function (report) {
		const company = frappe.query_report.get_filter_value("company");
		if (company) {
			frappe.db.get_value("Company", company, "default_warehouse_for_delivery", (r) => {
				if (r && r.default_warehouse_for_delivery) {
					report.set_filter_value("warehouse", r.default_warehouse_for_delivery);
				}
			});
		}
	},
};
