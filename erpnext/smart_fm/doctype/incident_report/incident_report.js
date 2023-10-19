// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Incident Report', {
  onload: function (frm) {
    frappe.db.get_value("User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"])
    .then(r => {
      let values = r.message;
      frm.set_value("name1", values.full_name);
      frm.set_value("email_address", values.email);
      frm.set_value("phone_number", values.phone);
    });
  },

	refresh: function(frm) {
    if (!frm.is_new()) {
			frm.add_custom_button(__("ToDo"), function() {
				frm.trigger("create_to_do");
			}, __("Create"));
    }
	},

	create_to_do: function(frm) {
		frappe.call({
			args: {
				"name": frm.doc.name,
      },
			method: "erpnext.smart_fm.doctype.incident_report.incident_report.create_to_do",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},
});
