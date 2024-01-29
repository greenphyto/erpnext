// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('FOMS Data Mapping', {
	view_in_console: function(frm) {
		console.log(JSON.parse(frm.doc.raw_data));
		frappe.show_alert("Plot to console",3)
	}
});
