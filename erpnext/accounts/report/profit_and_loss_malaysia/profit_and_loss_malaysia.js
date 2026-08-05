// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Profit and Loss Malaysia"] = $.extend({},
		erpnext.financial_statements);

	erpnext.utils.add_dimensions('Profit and Loss Malaysia', 10);

	// Remove filters: periodicity, from_fiscal_year, to_fiscal_year, accumulated_values
	var dominated_filters = ["periodicity", "to_fiscal_year", "accumulated_values"];
	frappe.query_reports["Profit and Loss Malaysia"]["filters"] = frappe.query_reports["Profit and Loss Malaysia"]["filters"].filter(function(f) {
		return dominated_filters.indexOf(f.fieldname) === -1;
	});

	// Rename from_fiscal_year to fiscal_year
	frappe.query_reports["Profit and Loss Malaysia"]["filters"].forEach(function(f) {
		if (f.fieldname === "from_fiscal_year") {
			f.fieldname = "fiscal_year";
			f.label = __("Fiscal Year");
		}
	});

	frappe.query_reports["Profit and Loss Malaysia"]["filters"].push(
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Project', txt);
			}
		},
		{
			"fieldname": "include_default_book_entries",
			"label": __("Include Default Book Entries"),
			"fieldtype": "Check",
			"default": 1
		},
		{
			"fieldname": "show_number_group",
			"label": __("Show Number Group"),
			"fieldtype": "Check",
			"default": 0
		},
		{
			"fieldname": "show_all_cost_centers",
			"label": __("Show on Cost Centers"),
			"fieldtype": "Check",
			"default": 0,
			"description": __("When enabled, columns are generated per Cost Center for the selected period(s).")
		}
	);

	frappe.query_reports["Profit and Loss Malaysia"]["formatter"] = function(value, row, column, data, default_formatter) {
		if (data && data.is_ratio && column.fieldtype === "Currency") {
			if (value === undefined || value === null || value === 0) {
				return "";
			}
			return (flt(value) * 100).toFixed(2) + "%";
		}
		value = default_formatter(value, row, column, data);
		if (data && (data.is_group || data.is_bold || (data.indent !== undefined && data.indent === 0))) {
			value = $(`<span>${value}</span>`);
			value = value.css("font-weight", "bold").wrap("<p></p>").parent().html();
		}
		return value;
	};

    frappe.query_reports["Profit and Loss Malaysia"]["onload"] = function(report){
        report.page.add_inner_button("Export with Cost Centers", function() {
            frappe.call({
                method: "erpnext.accounts.report.profit_and_loss_malaysia.profit_and_loss_malaysia.get_export_with_cost_centers_url",
                args: {
                    filters: report.get_values()
                },
                callback: function(r) {
                    if (r.message && r.message.url) {
                        window.open(r.message.url);
                    }
                }
            });
        });
    }
});
