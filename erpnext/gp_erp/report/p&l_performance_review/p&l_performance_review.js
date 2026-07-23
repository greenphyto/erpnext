// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

const P_L_MONTH_NAMES = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
];

frappe.query_reports["P&L Performance Review"] = {
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
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: frappe.defaults.get_user_default("fiscal_year"),
			reqd: 1,
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: [
				{ value: "YTD", label: __("YTD") },
				{ value: "Monthly", label: __("Monthly") },
			],
			default: "YTD",
			reqd: 1,
		},
		{
			fieldname: "to_month",
			label: __("Month"),
			fieldtype: "Select",
			options: P_L_MONTH_NAMES.join("\n"),
			default: P_L_MONTH_NAMES[new Date().getMonth()],
			reqd: 1,
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
		},
		{
			fieldname: "accumulated_values",
			label: __("Accumulated Values"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "hide_zero_balance",
			label: __("Hide Zero Balance"),
			fieldtype: "Check",
			default: 0,
		},
	],
	tree: true,
	name_field: "account",
	parent_field: "parent_account",
	initial_depth: 3,
	formatter: function (value, row, column, data, default_formatter) {
		if (data && column.fieldname == "account") {
			value = data.account_name || value;
			column.is_tree = true;
		}

		// Ratio rows (GOP%, Payroll%): show as percentage, skip currency formatter
		if (
			data &&
			data.ratio_row &&
			column.fieldname !== "account" &&
			column.fieldname !== "acc_code" &&
			column.fieldname !== "currency"
		) {
			let num = parseFloat(value) || 0;
			let display = num.toFixed(2) + "%";
			if (data.is_bold) {
				display = `<strong>${display}</strong>`;
			}
			if (num < 0) {
				display = `<span class="text-danger">${display}</span>`;
			}
			return display;
		}

		value = default_formatter(value, row, column, data);

		if (data && (data.is_group || data.is_bold || data.profit_data || data.ratio_row)) {
			value = $(`<span>${value}</span>`);
			var $value = $(value).css("font-weight", "bold");
			if (data.warn_if_negative && data[column.fieldname] < 0) {
				$value.addClass("text-danger");
			}
			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
};
