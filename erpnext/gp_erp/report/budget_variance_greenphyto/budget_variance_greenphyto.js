// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Budget Variance Greenphyto"] = $.extend({},
		erpnext.financial_statements);

	erpnext.utils.add_dimensions('Budget Variance Greenphyto', 10);
	
	frappe.query_reports["Budget Variance Greenphyto"]["filters"].push(
		{
			"fieldname": "accumulated_values",
			"label": __("Accumulated Values"),
			"fieldtype": "Check",
			"default": 1
		},
		{
			"fieldname": "hide_zero_balance",
			"label": __("Hide Zero Balance"),
			"fieldtype": "Check",
			"default": 0
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
