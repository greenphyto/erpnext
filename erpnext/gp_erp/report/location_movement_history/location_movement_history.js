// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Location Movement History"] = {
	"filters": [
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname": "action_type",
			"label": __("Action Type"),
			"fieldtype": "Select",
			"options": "\nNew\nMove\nDiscard",
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
			"fieldname": "user",
			"label": __("User"),
			"fieldtype": "Link",
			"options": "User",
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
		if (column.fieldname === "action_type") {
			const colors = { New: "green", Move: "blue", Discard: "red" };
			const color = colors[data.action_type] || "grey";
			value = `<span class="indicator-pill ${color}">${data.action_type || ""}</span>`;
		}
		return value;
	},
};
