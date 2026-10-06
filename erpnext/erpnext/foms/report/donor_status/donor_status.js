// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */
frappe.query_reports["Donor Status"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.year_start()
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.year_start()
		},
		{
			"fieldname": "sales_order",
			"label": "Sales Order",
			"fieldtype": "Link",
			"options": "Sales Order"
		},
		{
			"fieldname": "branch",
			"label": "Branch",
			"fieldtype": "Data",
			"options": ""
		}
	],
	formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname === "status") {
            const color = {
                "Draft":            "gray",
                "On Hold":          "gray",
                "To Deliver and Bill": "orange",
                "To Bill":          "orange", 
                "To Deliver":       "orange",
                "Completed":        "green",
                "Cancelled":        "red",
                "Closed":           "gray",
            }[data.status] || "gray";

            value = `<span class="indicator-pill ${color}">${data.status}</span>`;
        }
        
        return value;
    }
};
