// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Batch Location Report"] = {
	"filters": [
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
		},
		{
			"fieldname": "batch",
			"label": __("Batch"),
			"fieldtype": "Link",
			"options": "Batch",
		},
		{
			"fieldname": "item",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			get_query: () => ({
				filters: { is_stock_item: 1, disabled: 0 },
			}),
		},
		{
			"fieldname": "warehouse_location",
			"label": __("Warehouse Location"),
			"fieldtype": "Link",
			"options": "Warehouse Location",
		},
		{
			"fieldname": "aisle_row",
			"label": __("Aisle / Row"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "bay_column",
			"label": __("Bay / Column"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "level_tier",
			"label": __("Level / Tier"),
			"fieldtype": "Data",
		},
	],
	onload(report) {
		frappe.call({
			method: "erpnext.stock.doctype.warehouse_action.warehouse_action.get_action_context",
			callback(r) {
				if (r && r.message && r.message.warehouse) {
					report.set_filter_value("warehouse", r.message.warehouse);
				}
			},
		});
	},
};
