frappe.ready(function() {
	// bind events here
	frappe.validate_phone_field(['phone_number']);
	frappe.validate_email_field(['email_address']);


	if (frappe.web_form.in_edit_mode){
		var issued_field = frappe.web_form.fields_dict.issued_time;
		var issued = frappe.web_form.doc.issued;
		if (issued_field && issued==0){
			issued_field.set_value(frappe.datetime.now_datetime())
		}
		var returned_field = frappe.web_form.fields_dict.returned_time;
		var returned = frappe.web_form.doc.returned;
		if (returned_field && returned==0){
			returned_field.set_value(frappe.datetime.now_datetime())
		}
	}
})