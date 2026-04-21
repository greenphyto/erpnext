// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Batch Delivery"] = {
	"filters": [
		// Batch, item name and code, customer
		{
			"fieldname":"batch_no",
			"label": __("Batch No"),
			"fieldtype": "Link",
			"options":"Batch"
		},
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options":"Item",
			"get_query":()=>{
				return {
					filters:{
						"item_group":"Products"
					}
				}
			}
		},
		// {
		// 	"fieldname":"customer",
		// 	"label": __("Customer"),
		// 	"fieldtype": "Link",
		// 	"options":"Customer"
		// }
	]
};
