// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Balance Sheet Greenphyto"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1
		},
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
			"default": frappe.datetime.str_to_obj(frappe.datetime.get_today()).toLocaleString("en-US", { month: "long" }),
			"reqd": 1
		},
		{
			"fieldname": "include_default_book_entries",
			"label": __("Include Default Book Entries"),
			"fieldtype": "Check",
			"default": 1
		},
		{
			"fieldname": "ignore_closing_entries",
			"label": __("Ignore Closing Entry"),
			"fieldtype": "Check",
			"default": 0
		},
	],
	"tree": true,
	"name_field": "account",
	"parent_field": "parent_account",
	"initial_depth": 3,
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && (data.is_group || data.is_bold || (data.indent !== undefined && data.indent === 0))) {
			value = $(`<span>${value}</span>`);
			value = value.css("font-weight", "bold").wrap("<p></p>").parent().html();
		}
		return value;
	}
};
