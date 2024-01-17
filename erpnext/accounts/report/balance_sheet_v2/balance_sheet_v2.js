// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Balance Sheet V2"] = $.extend({}, erpnext.financial_statements);

	erpnext.utils.add_dimensions('Balance Sheet V2', 10);

	frappe.query_reports["Balance Sheet V2"]["filters"].push({
		"fieldname": "accumulated_values",
		"label": __("Accumulated Values"),
		"fieldtype": "Check",
		"default": 1
	});

	frappe.query_reports["Balance Sheet V2"]["filters"].push({
		"fieldname": "include_default_book_entries",
		"label": __("Include Default Book Entries"),
		"fieldtype": "Check",
		"default": 1
	});

	frappe.query_reports["Balance Sheet V2"]["filters"].push({
		"fieldname": "ignore_closing_entries",
		"label": __("Ignore Closing Entry"),
		"fieldtype": "Check",
		"default": 1
	});

	frappe.query_reports["Balance Sheet V2"]["filters"].push({
		"fieldname": "show_number_group",
		"label": __("Show Number Group"),
		"fieldtype": "Check",
		"default": 0
	});
});
