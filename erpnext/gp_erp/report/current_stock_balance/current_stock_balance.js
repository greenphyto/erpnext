// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Current Stock Balance"] = {
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
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"get_query": function () {
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
			"fieldname": "item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query": function () {
				return {
					filters: {
						"has_batch_no": 1
					}
				};
			}
		}
	],
	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.is_group_total) {
			value = `<b>${value}</b>`;
		}
		if (column.fieldname == "difference" && data && data.difference && Math.abs(data.difference) > 0) {
			value = `<span style="color: var(--red-600)">${value}</span>`;
		}
		return value;
	},
	"onload": function (report) {
		report.page.add_inner_button(__("Create Stock Reconciliation"), function () {
			let filters = report.get_values();
			if (!filters.company || !filters.date) {
				frappe.msgprint(__("Please set Company and Date"));
				return;
			}
			frappe.call({
				method: "erpnext.gp_erp.report.current_stock_balance.current_stock_balance.make_stock_reconciliation",
				args: {
					filters: filters
				},
				freeze: true,
				freeze_message: __("Creating Stock Reconciliation..."),
				callback: function (r) {
					if (r.message) {
						let doc = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", doc.doctype, doc.name);
					}
				}
			});
		});
	}
};
