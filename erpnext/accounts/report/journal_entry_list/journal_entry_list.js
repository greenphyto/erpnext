// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Journal Entry List"] = {
	"filters": [
		{
			"fieldname":"order_by",
			"label": __("Order By"),
			"fieldtype": "Select",
			"options": "Name\nDate",
			"default":"Date"
		},
		{
			"fieldname":"name",
			"label": __("ID"),
			"fieldtype": "Data",
			"width": 100,
		},
		// {
		// 	"fieldname":"period_start_date",
		// 	"label": __("Start Date"),
		// 	"fieldtype": "Date",
		// 	"reqd": 1,
		// 	"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		// },
		// {
		// 	"fieldname":"period_end_date",
		// 	"label": __("End Date"),
		// 	"fieldtype": "Date",
		// 	"reqd": 1,
		// 	"default": frappe.datetime.get_today()
		// },		
	]
};
