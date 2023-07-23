// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Asset Maintenance Log"] = {
	"filters": [
		{
			"fieldname": "item_code",
			"fieldtype": "Link",
			"label": "Item Code",
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
			"fieldname": "task_name",
			"fieldtype": "Data",
			"label": "Task Name",
		},
		{
			"fieldname": "maintenance_type",
			"fieldtype": "Select",
			"label": "Maintenance Type",
			"options": "\nPreventive Maintenance\nCalibration"
		},
		{
			"fieldname": "periodicity",
			"fieldtype": "Select",
			"label": "Periodicity",
			"options": "\nOnce\nDaily\nWeekly\nMonthly\nQuarterly\nYearly\n2 Yearly\n3 Yearly",
		},
		{
			"fieldname": "maintenance_status",
			"fieldtype": "Select",
			"label": "Maintenance Status",
			"options": "Planned\nOverdue\nCancelled",
		},
		{
			"fieldname": "assign_to_name",
			"fieldtype": "Data",
			"label": "Assign To",
		},
	]
};
