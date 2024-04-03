// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Information Security Incident Report', {
	onload: function (frm) {
		if (frm.is_new()) {
			frappe.db.get_value("User", frappe.session.user, ["full_name", "phone", "mobile_no"])
				.then(r => {
					let values = r.message;
					frm.set_value("reported_by", values.full_name);
			});
		}
	},
});
