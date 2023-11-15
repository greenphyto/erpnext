// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Facilities Service Reservation', {
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
	from_time: function(frm){
		frm.cscript.set_total_duration();
	},
	to_time: function(frm){
		frm.cscript.set_total_duration();
	}
});

frappe.provide("cur_frm.cscript")
$.extend(cur_frm.cscript, {
	set_total_duration(){
		var frm = this.frm;
		var seconds = (moment(frm.doc.to_time) - moment(frm.doc.from_time)) /1000
		frm.set_value("total_duration", seconds);
	}
})