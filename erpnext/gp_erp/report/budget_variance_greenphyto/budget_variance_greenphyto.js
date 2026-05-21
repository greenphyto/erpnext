// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
frappe.provide("erpnext.financial_statements");

erpnext.financial_statements = {
	"filters": get_filters(),
	"formatter": function(value, row, column, data, default_formatter) {
		if (data && column.fieldname=="account") {
			value = data.account_name || value;

			column.link_onclick =
				"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(data) + ")";
			column.is_tree = true;
		}

		value = default_formatter(value, row, column, data);

		if (data && data.is_group) {
			value = $(`<span>${value}</span>`);

			var $value = $(value).css("font-weight", "bold");
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
	"tree": true,
	"name_field": "account",
	"parent_field": "parent_account",
	"initial_depth": 3,
	onload: function(report) {
		// dropdown for links to other financial statements
		erpnext.financial_statements.filters = get_filters()

		let fiscal_year = frappe.defaults.get_user_default("fiscal_year")

		frappe.model.with_doc("Fiscal Year", fiscal_year, function(r) {
			var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
			frappe.query_report.set_filter_value({
				period_start_date: fy.year_start_date,
				period_end_date: fy.year_end_date
			});
		});

		const views_menu = report.page.add_custom_button_group(__('Financial Statements'));

		report.page.add_custom_menu_item(views_menu, __("Balance Sheet"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Balance Sheet', {company: filters.company});
		});

		report.page.add_custom_menu_item(views_menu, __("Profit and Loss"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Profit and Loss Statement', {company: filters.company});
		});

		report.page.add_custom_menu_item(views_menu, __("Cash Flow Statement"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Cash Flow', {company: filters.company});
		});
	}
};

function get_filters() {
	let filters = [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1
		},
		{
			"fieldname":"month",
			"label": __("From Month"),
			"fieldtype": "Select",
			"reqd": 0,
			"options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
		},
		{
			"fieldname":"to_month",
			"label": __("To Month"),
			"fieldtype": "Select",
			"reqd": 0,
			"options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
		},
		{
			"fieldname": "periodicity",
			"label": __("Periodicity"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Yearly", "label": __("Yearly") },
			],
			"default": "Yearly",
			"reqd": 1
		},
		// Note:
		// If you are modifying this array such that the presentation_currency object
		// is no longer the last object, please make adjustments in cash_flow.js
		// accordingly.
		{
			"fieldname": "presentation_currency",
			"label": __("Currency"),
			"fieldtype": "Select",
			"options": erpnext.get_presentation_currency_list()
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Cost Center', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		}
	]

	return filters;
}



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
