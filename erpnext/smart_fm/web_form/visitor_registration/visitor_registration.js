frappe.ready(function() {
	// bind events here
	frappe.web_form.on("person", (frm, value)=>{
		if (value=="Yes"){
			// add child based on user login
			if ( is_null(frappe.web_form.doc.person_list) ){
				frappe.db.get_value("User", frappe.session.user, [
					'full_name as name1', 
					'email',
					'phone as phone_number'])
				.then(r=>{ 
					frappe.web_form.doc.person_list = [r.message]
					frappe.web_form.refresh_fields([{
						fieldname:'person_list'
					}]);
				});
			}
		}else{
			frappe.web_form.doc.person_list = []
		}
	})

	frappe.validate_phone_field(['phone_number']);
	frappe.validate_email_field(['email_address']);

	frappe.validate_phone_field_table('person_list', 'phone_number');

	// set disable edit when submit
	var doc = frappe.web_form.doc;

	if (doc.docstatus != 0){
		$(".edit-button").hide();
	}

	var check_in_field = frappe.web_form.fields_dict.check_in_time;
	var check_in = frappe.web_form.doc.check_in;
	if (check_in_field && check_in==0){
		check_in_field.set_value(frappe.datetime.now_datetime())
	}
	var check_out_field = frappe.web_form.fields_dict.check_out_time;
	var check_out = frappe.web_form.doc.check_out;
	if (check_out_field && check_out==0){
		check_out_field.set_value(frappe.datetime.now_datetime())
	}
});