// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Part Number"] = {
	onload: function(report){
		report.page.add_button(__("Edit Settings"), function() {
			frappe.set_route('Form', 'Part Number Settings');
		}, {
			btn_class: "btn-primary btn-edit-settings"
		});
		$(report.page.parent).append(`
			<style> .custom-actions > button:not(.btn-edit-settings) { display: none; }</style>
		`)
	}
};
