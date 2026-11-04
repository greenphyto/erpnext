// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Work Order Cost Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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
			fieldname: "production_item",
			label: __("Production Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				return { filters: { is_stock_item: 1 } };
			},
		},
		{
			fieldname: "merge_summary",
			label: __("Merge Summary"),
			fieldtype: "Check",
			default: 0,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldname === "voucher_no" && value) {
			const prefix = String(value).substring(0, 2).toUpperCase();
			const se_color_map = {
				SE: "yellow", // Seeding Transfer
				TR: "green", // Transplanting Transfer
				HR: "blue", // Harvesting Transfer
				HA: "purple", // Harvesting Finish / Manufacture
			};
			const safe = frappe.utils.escape_html(value);
			if (se_color_map[prefix]) {
				const href = `/app/stock-entry/${encodeURIComponent(value)}`;
				return `<a href="${href}" class="indicator-pill ${se_color_map[prefix]}" style="text-decoration:none;">${safe}</a>`;
			}
			// Journal Entry (actual payments) -> grey pill linking to the JE
			if (prefix === "AC" || String(value).indexOf("JV") !== -1) {
				const href = `/app/journal-entry/${encodeURIComponent(value)}`;
				return `<a href="${href}" class="indicator-pill gray" style="text-decoration:none;">${safe}</a>`;
			}
		}
		return default_formatter(value, row, column, data);
	},
};
