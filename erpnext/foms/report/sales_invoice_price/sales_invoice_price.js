// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales Invoice Price"] = {
    filters: [
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_default("company"),
            reqd: 1
        },
        {
            fieldname: "posting_date",
            label: "Posting Date",
            fieldtype: "Date",
            options: ""
        },
        {
            fieldname: "work_order",
            label: "Work Order ID",
            fieldtype: "Link",
            options: "Work Order"
        },
        {
            fieldname: "operation",
            label: "Operation",
            fieldtype: "Select",
            options: "\nSeeding\nTransplanting", 
        },
        {
            fieldname: "item_code",
            label: "Product (Item)",
            fieldtype: "Link",
            options: "Item"
        }
    ]
};
