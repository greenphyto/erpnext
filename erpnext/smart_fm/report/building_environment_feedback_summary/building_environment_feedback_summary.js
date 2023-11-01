// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Building Environment Feedback Summary"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": "Date From",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": "Date To",
			"default": frappe.datetime.get_today()
		},
	],
	"formatter": function(value, row, column, data, default_formatter) {
		if (value=="Button"){
			console.log("Here")
		}
		value = default_formatter(value, row, column, data);
		if (data && data.is_group) {
			value = value.bold();
			console.log(16, value)
		}
		if (value=="Button"){
			return `<div>
				<a 
					msg_field="${data.msg_field}"
					onClick="frappe.report_script.show_messages(this);" 
					style="font-size: 0.82em;color: #aeaeae;"
				>Show Message</a>
			</div>`
		}
		return value;
	},
};

frappe.provide("frappe.report_script")
frappe.report_script = {
	show_messages:function(el){
		console.log("show", el)
	}
}