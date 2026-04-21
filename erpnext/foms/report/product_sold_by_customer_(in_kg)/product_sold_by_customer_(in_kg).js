// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Product Sold by Customer (in Kg)"] = {
	"filters": [
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Link",
            default: frappe.datetime.get_today().split("-")[0],
            options: "Fiscal Year",
            reqd: 1
        },
		{
			"fieldname": "customer",
			"label": "Customer",
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "item_code",
			"label": "Item Code",
			"fieldtype": "Link",
			"options": "Item"
		}
	]
};
