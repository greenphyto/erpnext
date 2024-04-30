// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Visitor Registration', {
  onload: function (frm) {
    if (frm.is_new()) {
      frappe.db.get_value("User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"])
      .then(r => {
        let values = r.message;
        frm.set_value("name1", values.full_name);
        frm.set_value("email_address", values.email);
        frm.set_value("phone_number", values.phone);
      });
      frm.set_value("company", frappe.defaults.get_user_default("Company"));
    }
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
			method: "erpnext.smart_fm.doctype.access_request.access_request.create_to_do",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	person: function(frm){
		if (frm.doc.person!="No"){
			// add child based on user login
			if ( is_null(frm.doc.person_list) ){
				// frappe.db.get_value("User", frappe.session.user, [
				// 	'full_name as name1', 
				// 	'email',
				// 	'phone as phone_number'])
				// .then(r=>{ 
				// 	var row = frm.add_child("person_list", r.message);
				// 	frm.refresh_field("person_list");
				// });
        frm.set_value("person_list", [{}]);
			}
		}else{
			frm.set_value("person_list", []);
			frm.refresh_field("person_list");
		}
	}
});
