// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Item Price and Invoice"] = {
	"filters": [
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options":"Item",
			"get_query":()=>{
				return {
					filters:{
						"item_group":"Products",
						"disabled":0
					}
				}
			}
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options":"Customer",
			"get_query":()=>{
				return {
					filters:{
						"disabled":0,
					}
				}
			}
		},
				{
			"fieldname":"invoice",
			"label": __("Invoice"),
			"fieldtype": "Link",
			"options":"Sales Invoice",
			"get_query":()=>{
				return {
					filters:{
						"is_return":0,
						"docstatus":1,
					}
				}
			}
		}
	]
};
