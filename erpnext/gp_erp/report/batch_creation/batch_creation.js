// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Batch Creation"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"get_query": function() {
				let company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						"company": company
					}
				};
			}
		},
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"default": "Products"
		},
		{
			"fieldname": "item",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query": function() {
				return {
					filters: {
						"has_batch_no": 1
					}
				};
			}
		},
		{
			"fieldname": "show_only_active_batch",
			"label": __("Show Only Active Batch"),
			"fieldtype": "Check",
			"default": 1
		}
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "status" && data && data.status) {
			let colors = { "Active": "green", "Expired": "red", "Empty": "gray" };
			let color = colors[data.status] || "gray";
			value = `<span class="indicator-pill ${color}">${__(data.status)}</span>`;
		}

		return value;
	}
};
