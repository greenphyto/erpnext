// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GST Return Summary Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -2),
			"width": "80"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "frequency",
			"fieldtype": "Select",
			"label": __("Frequency"),
			"reqd": 1,
			"options": [
				{ "label": __("Monthly"), value: "Monthly" },
				{ "label": __("Quarterly"), value: "Quarterly" },
				{ "label": __("Yearly"), value: "Yearly" },
			],
			"on_change": function(query_report) {
					var frequency  = query_report.get_values().frequency;
					if (frequency == 'Monthly')
					 	{ 
							var date = new Date();
							var firstDay = new Date(date.getFullYear(),
											date.getMonth(), 1);
							var lastDay = new Date(date.getFullYear(),
											date.getMonth(), daysInMonth(date.getMonth()+1,
											date.getFullYear()));
						}
					else if (frequency=='Quarterly')
						{
							var today = new Date();
							var quarter = Math.floor((today.getMonth() / 3));
							firstDay =  new Date(today.getFullYear(), quarter * 3, 1);
							lastDay = new Date(firstDay.getFullYear(), firstDay.getMonth() + 3, 0);
						}
					else
						{
							var date = new Date();
							var firstDay = new Date(date.getFullYear(),
											0, 1);
							var lastDay = new Date(date.getFullYear(),
											11,  31);
						}
					frappe.query_report.set_filter_value({
						from_date: firstDay ,
						to_date: lastDay
					});
				 
			}
		}
	]
};
function daysInMonth (month, year) {
	return new Date(year, month, 0).getDate();
}