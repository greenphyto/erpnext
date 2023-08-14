// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Utility Report"] = {
	"filters": [
		{
			"fieldname": "date_from",
			"fieldtype": "Date",
			"label": "Date From",
		},
		{
			"fieldname": "date_to",
			"fieldtype": "Date",
			"label": "Date To",
		},
		{
			"fieldname": "type_of_meter",
			"fieldtype": "Select",
			"label": "Type of Meter",
			"options": "\nElectricity\nWater\nGas",
		},
		{
			"fieldname": "utility",
			"fieldtype": "Link",
			"label": "Utility",
			"options": "Utility",
			get_query: function(){
				var filters = {};
				var type_meter = frappe.query_report.get_filter_value("type_of_meter");
				if (type_meter){
					return {
						filters:{
							type_of_meter: frappe.query_report.get_filter_value("type_of_meter")
						}
					}
				}else{
					return filters
				}
			}
		},
	]
};
