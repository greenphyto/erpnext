frappe.query_reports["Picking List Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1,
            "width": 100
        },
        {
            "fieldname": "date",
            "label": __("Delivery Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "view_type",
            "label": __("View Type"),
            "fieldtype": "Select",
            "reqd": 1,
            "hidden": 1,
            "default": "All Outlets",
			"options":"All Outlets\nDelivery Note"
        },
		{
            "fieldname": "status",
            "label": __("Document Status"),
            "fieldtype": "Select",
            "reqd": 1,
            "default": "All",
			"options":"All\nDraft\nSubmitted"
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname != "outlets" && row && row[0].rowIndex==1 && !value.includes("div")) {
            var indi = data[column.fieldname+"_status"] == 0 ? 'red' : 'blue';
            value = `<a class="indicator ${indi}" href="/app/delivery-note/${value}" target="_blank" rel="noopener noreferrer">${value}</a>`;
        }
        
        return value;
    }
};
