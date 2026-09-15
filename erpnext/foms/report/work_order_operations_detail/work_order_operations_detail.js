// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Work Order Operations Detail"] = {
	filters: [
		{
			fieldname: "from_date",
			label: "From Date",
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: "To Date",
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "work_order",
			label: "Work Order",
			fieldtype: "Link",
			options: "Work Order",
		},
		{
			fieldname: "product",
			label: "Item",
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "wo_status",
			label: "Work Order Status",
			fieldtype: "Select",
			options: [
				"Not Started",
				"In Process",
				"Completed",
				"Stopped",
				"Closed",
				"Cancelled",
			].join("\n"),
			default: "Completed",
		},
		{
			fieldname: "show_all_materials",
			label: "Show All Materials",
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "show_total_source_materials",
			label: "Show Total Source Materials",
			fieldtype: "Check",
			default: 0,
			depends_on: "eval:doc.show_all_materials==1",
			description: "Insert subtotal before Harvesting Finished Goods target rows",
		},
	],
};
