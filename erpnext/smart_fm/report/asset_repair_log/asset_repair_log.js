// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Asset Repair Log"] = {
	"filters": [
		{
			"fieldname": "asset",
			"fieldtype": "Link",
			"label": "Asset",
			"options": "Item",
			get_query: ()=>{
				return {
					filters:{
						is_fixed_asset: 1
					}
				}
			}
		},
		{
			"fieldname": "request_id",
			"fieldtype": "Link",
			"label": "Request ID",
			"options": "Maintenance Request",
		},
		{
			"fieldname": "repair_status",
			"fieldtype": "Select",
			"label": "Repair Status",
			"options": "\nPending\nCompleted\nCancelled"
		},
		{
			"fieldname": "failure_date",
			"fieldtype": "Date",
			"label": "Failure Date",
		},
		{
			"fieldname": "completion_date",
			"fieldtype": "Date",
			"label": "Completion Date",
		},
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = value.bold();
		}

		if (column.fieldname=="repair_status"){
			colors = {
				"Pending":"blue",
				"Cancelled":"red",
				"Completed":"green",
			}
			value = `<div style="color:${colors[value]};">${value}</div>`
		}

		if (column.fieldname=="asset_name"){
			value = `<a href="/app/asset/${data.asset}">${data.asset_name}</a>`
		}
		return value;
	},
};
