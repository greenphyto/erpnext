// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Warehouse Location View"] = {
	"filters": [
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nAvailable\nOccupied\nPartial\nBlocked",
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
		{
			"fieldname": "batch",
			"label": __("Batch"),
			"fieldtype": "Link",
			"options": "Batch",
		},
		{
			"fieldname": "show_disabled",
			"label": __("Show Disabled"),
			"fieldtype": "Check",
			"default": 0,
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
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status") {
			const colors = {
				Available: "green",
				Partial: "orange",
				Occupied: "red",
				Blocked: "grey",
			};
			const color = colors[data.status] || "grey";
			value = `<span class="indicator-pill ${color}">${data.status || ""}</span>`;
		}
		return value;
	},
};
