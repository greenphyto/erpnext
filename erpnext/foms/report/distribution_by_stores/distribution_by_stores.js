// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Distribution by Stores"] = {
	"filters": [
		{
			"fieldname":"start_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"options":""
		},
		{
			"fieldname":"end_date",
			"label": __("End Dtae"),
			"fieldtype": "Date",
			"options":""
		},
	],
	"onload": function(report) {
		const today = frappe.datetime.get_today();
		const startOfMonth = frappe.datetime.month_start(today);
		const endOfMonth = frappe.datetime.month_end(today);

		frappe.query_report.set_filter_value("start_date", startOfMonth);
		frappe.query_report.set_filter_value("end_date", endOfMonth);

	},
	get_datatable_options: function(options){
		options.inlineFilters = false;
		return options
	},
	formatter:function(value, row, column, data, default_formatter) {
		if (row.meta.rowIndex==0){
			value = `<div style='text-align: center'>${value || ""}</div>`
		} else if (column.colIndex==1){
			value = `<div style='text-align: center'>${value || ""}</div>`
		} else{
			value = default_formatter(value, row, column, data);
		}
		return value;
	},
	after_datatable_render: function(dt){
		dt.style.setStyle(".dt-cell--col-0", {"display":"none !important"})
		dt.style.setStyle(".dt-cell--col-1", {"position":"sticky", "left":0, "z-index":1})
		dt.style.setStyle(".dt-cell--col-2", {"position":"sticky", "left":"50px", "z-index":1, "border-right":"1px solid #bcbcbc", "background-color":"white"})
		dt.style.setStyle(".dt-row-0", {
			"z-index": 2,
			"border-bottom": "1px solid #bcbcbc",
			"background-color":"white"
		})


		var scrollBody = dt.wrapper.querySelector(".dt-scrollable");

		if (scrollBody) {
			scrollBody.addEventListener("scroll", (e) => {
			const scrollTop = e.target.scrollTop;
			const scrollLeft = e.target.scrollLeft;
			var new_pos = scrollLeft + 50;
			dt.style.setStyle(".dt-row-header > .dt-cell--col-1", {"transform":`translateX(${scrollLeft}px)`})
			dt.style.setStyle(".dt-row-header > .dt-cell--col-2", {"transform":`translateX(${scrollLeft}px)`})
			dt.style.setStyle(".dt-row-0", {"transform":`translateY(${scrollTop}px)`})
			});
		}
	},
	
};
