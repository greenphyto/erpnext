// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Part Number Group Detail"] = {
	"filters": [
		{
			"fieldname": "part_number_group",
			"label": __("Part Number Group"),
			"fieldtype": "Link",
			"options": "Part Number Group"
		},
		{
			"fieldname": "item_default",
			"label": __("Item Default"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "part_number",
			"label": __("Part Number"),
			"fieldtype": "Data"
		}
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data || !value) return value;

		let doctype, name;
		if (column.fieldname === "name_col") {
			if (data.indent === 0) {
				doctype = "part-number-group";
				name = data.part_number_group;
			} else {
				doctype = "item";
				name = data.item_code;
			}
		} else if (column.fieldname === "part_number" && data.item_code) {
			doctype = "item";
			name = data.item_code;
		}

		if (!name) return value;
		return `<a href="/app/${doctype}/${encodeURIComponent(name)}">${value}</a>`;
	}
};
