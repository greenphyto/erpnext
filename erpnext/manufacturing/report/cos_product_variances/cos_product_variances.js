// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["COS Product Variances"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(new Date(), -1)
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": "Today"
		},
		{
			"fieldname":"product",
			"label": __("Product"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query":()=>{
				return {
					filters: {
						foms_product_id:['is', 'set'],
						disabled:0
					}
				}
			}
		},
		{
			"fieldname":"work_order",
			"label": __("Work Order"),
			"fieldtype": "Link",
			"options": "Work Order"
		}
	]
};
