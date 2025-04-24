// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('UOB Integration Settings', {
	get_file_list: function(frm) {
		frappe.show_alert("in progres");
		frappe.call({
			method:"get_file_list",
			doc:frm.doc,
			callback:r=>{
				console.log(r)
			}
		})
	}
});
