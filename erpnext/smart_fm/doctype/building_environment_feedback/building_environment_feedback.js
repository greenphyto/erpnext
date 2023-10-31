// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Building Environment Feedback', {
	onload: function (frm) {
		if (frm.is_new()) {
		  frappe.db.get_value("User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"])
		  .then(r => {
			let values = r.message;
			frm.set_value("full_name", values.full_name);
			frm.set_value("email_address", values.email);
		  });
		}
	},
});
