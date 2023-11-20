frappe.ready(function() {
	// bind events here
	console.log("here")
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

	frappe.validate_phone_field_table('person_list', 'phone_number');
})