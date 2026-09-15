// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Product Returns"] = {
    filters: [
        {
            fieldname: "view_type",
            label: "View Type",
            fieldtype: "Select",
            options: ["Monthly", "Daily"],
            default: "Monthly",
            reqd: 1
        },
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Link",
            default: frappe.datetime.get_today().split("-")[0],
            options: "Fiscal Year",
            reqd: 1
        },
        {
            fieldname: "month",
            label: "Month",
            fieldtype: "Select",
            options: [
                "", "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ],
            default: frappe.datetime.get_today().split("-")[1],
            depends_on: "eval: doc.view_type == 'Daily'"
        },
        {
            fieldname: "customer",
            label: "Customer",
            fieldtype: "Link",
            options: "Customer"
        }
    ]
}
