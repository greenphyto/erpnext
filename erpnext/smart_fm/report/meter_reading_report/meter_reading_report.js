// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Meter Reading Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": "From Date",
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": "To Date",
		},
		{
			"fieldname": "group_by",
			"fieldtype": "Select",
			"label": "Group By",
			"options": "Utility\nType of Meter",
			"default": "Utility",
			on_change: function(){
				var value = frappe.query_report.get_filter_value("group_by");
				var filter = frappe.query_report.get_filter("type_of_meter");
				if (value == "Type of Meter"){
					filter.df.hidden = 1;
				}else{
					filter.df.hidden = 0;
				}
				filter.refresh();
				console.log("here")
			}
		},
		{
			"fieldname": "type_of_meter",
			"fieldtype": "Select",
			"label": "Type of Meter",
			"options": "Electricity\nWater\nGas",
			"default": "Electricity"
		},
		{
			"fieldname": "utility",
			"fieldtype": "Link",
			"label": "Utility",
			"options": "Utility"
		},
		{
			"fieldname": "meter_location",
			"fieldtype": "Link",
			"label": "Meter Location",
			"options": "Location",
		},
	]
};
