// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["FOMS Raw Material Status"] = {
	"filters": [
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			reqd: 1,
			get_query: ()=>{
				return {
					filters:{
						item_group: "Raw Material",
						disabled: 0,
					}
				}
			}
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			default: "Stores - GPL",
			reqd: 1
		},
		// {
		// 	fieldname: "batch_no",
		// 	label: __("Batch"),
		// 	fieldtype: "Link",
		// 	options: "Batch",
		// 	reqd: 0
		// },
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["Reserved", "Available", "Issued"].join("\n"),
			reqd: 0
		}
	]
};
