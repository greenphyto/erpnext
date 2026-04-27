// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Budget Variance Greenphyto"] = $.extend({},
		erpnext.financial_statements);

	erpnext.utils.add_dimensions('Budget Variance Greenphyto', 10);

	// Add Accumulated Values toggle
	frappe.query_reports["Budget Variance Greenphyto"]["filters"].push({
		"fieldname": "accumulated_values",
		"label": __("Accumulated Values"),
		"fieldtype": "Check",
		"default": 1
	});

	frappe.query_reports["Budget Variance Greenphyto"]["filters"].push(
		// {
		// 	"fieldname": "project",
		// 	"label": __("Project"),
		// 	"fieldtype": "MultiSelectList",
		// 	get_data: function(txt) {
		// 		return frappe.db.get_link_options('Project', txt);
		// 	}
		// },
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

	frappe.query_reports["Budget Variance Greenphyto"]["onload"] = function(report){
        report.page.add_inner_button("Export with Cost Centers", function() {
            frappe.call({
                method: "erpnext.gp_erp.report.budget_variance_greenphyto.budget_variance_greenphyto.get_export_with_cost_centers_url",
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
