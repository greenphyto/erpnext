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

	person: function(frm){
		if (frm.doc.person!="No"){
			// add child based on user login
			if ( is_null(frm.doc.person_list) ){
				frappe.db.get_value("User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"])
				.then(r => {
					let values = r.message;
					frm.set_value("person_list", [{name1: values.full_name, phone_number: values.phone, email: values.email}]);
				});
			}
		}else{
			frm.set_value("person_list", []);
			frm.refresh_field("person_list");
		}
	},

	get_sign_in: function(frm){
		frm.set_value("check_in", frappe.datetime.now_datetime());
	},

	get_sign_out: function(frm){
		frm.set_value("check_out", frappe.datetime.now_datetime());
	}
});


console.log("123")