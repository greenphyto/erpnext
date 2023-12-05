// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Asset Depreciations and Balances"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date"),
			"reqd": 1
		},
		{
			"fieldname":"asset_category",
			"label": __("Asset Category"),
			"fieldtype": "Link",
			"options": "Asset Category"
		},
		{
			"fieldname":"show_asset",
			"label": __("Show Asset"),
			"fieldtype": "Check",
			"default": 1
		},
		{
			"fieldname":"ignore_entry",
			"label": __("Ignore Depreciation Entry"),
			"fieldtype": "Check",
			"default": 1
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		if ((flt(value)>0 || value==0) && column.fieldtype=="Currency"){
			value = frappe.format(flt(value), {"fieldtype":"Currency", precision:2});
		}

		if (column.fieldtype=="Link"){
			value = default_formatter(value, row, column, data)
		}

		if (data.bold && value) {
			var $value = $(value).css("font-weight", "bold");
			value = $value.wrap("<p></p>").parent().html();
			return value
		}

		if (!value && value!=0) return "";

		return value
	},
}
