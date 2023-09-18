// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Statement of Account (Outstanding)"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd":1
		},
		{
			"fieldname":"party_type",
			"label": __("Party Type"),
			"fieldtype": "Select",
			"options": "Customer\nSupplier",
			"default": "Customer",
			"reqd":1
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"depends_on": "eval:doc.party_type == 'Customer'",
			"mandatory_depends_on": "eval:doc.party_type == 'Customer'",
		},
		{
			"fieldname":"supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"depends_on": "eval:doc.party_type == 'Supplier'",
			"mandatory_depends_on": "eval:doc.party_type == 'Supplier'",
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"width": "80"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		// {
		// 	"fieldname": "presentation_currency",
		// 	"label": __("Currency"),
		// 	"fieldtype": "Select",
		// 	"options": erpnext.get_presentation_currency_list(),
		// 	"default": frappe.defaults.get_user_default("Currency")
		// },
	],
	"onload": function(report){
		return new Promise(resolve=>{
			console.log("end")
			setTimeout(()=>{
				console.log("start")
			}, 5000)
		})
	}
};
