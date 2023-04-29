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
			"default": new Date(new Date().getFullYear(), Math.floor(new Date().getMonth() / 3) * 3, 1),//frappe.datetime.add_months(frappe.datetime.get_today(), -2),
			"width": "80"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": new Date(new Date().getFullYear(), Math.floor(new Date().getMonth() / 3) * 3 + 3, 0)//frappe.datetime.get_today()
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
			"default": "Quarterly",
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
		},
		{
			"fieldname": "show_details",
			"label": __("Show Details"),
			"fieldtype": "Check",
		},
	],
	"formatter": function(value, row, column, data, default_formatter) {
		if (data && column.fieldname=="posting_date" ) {
			value = data.account_name || value;

			column.link_onclick =
				"open_general_ledger(" + JSON.stringify(data) + ")";
			column.is_tree = true;
			
		}

		value = default_formatter(value, row, column, data);

		if (data && !data.parent_account) {
			value = $(`<span>${value}</span>`);
			var $value = $(value).css("color", "black");
			if(column.link_onclick && column.link_onclick.includes("voucher_type")){
				  $value = $(value).css("color", "blue");
			}
			if (data.warn_if_negative && data[column.fieldname] < 0) {
				$value.addClass("text-danger");
			}

			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
	"open_general_ledger": function(data) {
		if (!data.account) return;
		let project = $.grep(frappe.query_report.filters, function(e){ return e.df.fieldname == 'project'; });

		frappe.route_options = {
			"account": data.account,
			"company": frappe.query_report.get_filter_value('company'),
			"from_date": data.from_date || data.year_start_date,
			"to_date": data.to_date || data.year_end_date,
			"project": (project && project.length > 0) ? project[0].$input.val() : ""
		};

		let report = "General Ledger";

		if (["Payable", "Receivable"].includes(data.account_type)) {
			report = data.account_type == "Payable" ? "Accounts Payable" : "Accounts Receivable";
			frappe.route_options["party_account"] = data.account;
			frappe.route_options["report_date"] = data.year_end_date;
		}

		frappe.set_route("query-report", report);
	},
};
function daysInMonth (month, year) {
	return new Date(year, month, 0).getDate();
}
function open_general_ledger(data,query_report) {
	if (!data.voucher_type) return;
	let project = $.grep(frappe.query_report.filters, function(e){ return e.df.fieldname == 'project'; });

	frappe.route_options = {
		"account": data.account,
		"company": frappe.query_report.get_filter_value('company'),
		"from_date": frappe.query_report.get_values().from_date || data.year_start_date,
		"to_date": frappe.query_report.get_values().to_date || data.year_end_date,
		"project": (project && project.length > 0) ? project[0].$input.val() : ""
	};

	let report = "General Ledger";

	if (["Sales Invoice", "Purchase Invoice"].includes(data.voucher_type)) {
		report = data.voucher_type == "Sales Invoice" ? "Sales Taxes" : "Purchase Taxes";
		frappe.route_options["party_account"] = data.account;
		frappe.route_options["report_date"] = data.year_end_date;
	}

	frappe.set_route("query-report", report);
}
