frappe.ready(function() {
	console.log("from here")
	// bind events here
	frappe.web_form.on("person", (frm, value)=>{
		if (value=="Yes"){
			// add child based on user login
			frappe.web_form.doc.person_list = [{
				"name1":frappe.web_form.doc.name1,
				"email":frappe.web_form.doc.email,
				"phone_number":frappe.web_form.doc.phone_number,
			}]
		}else{
			frappe.web_form.doc.person_list = []
		}
		frappe.web_form.refresh_fields([{
			fieldname:'person_list'
		}]);
	});

	frappe.web_form.on("phone_number", (frm, value)=>{
		if (!frappe.utils.validate_type( value, 'phone')){
			frappe.web_form.set_value("phone_number", "")
		}

		if (value && is_null(frappe.web_form.doc.area_resource)){
			frappe.call({
				method:"erpnext.smart_fm.doctype.visitor_registration.visitor_registration.find_data_by_phone_number",
				args:{
					number:frappe.web_form.doc.phone_number
				},
				callback: res=>{
					res = res.message;
					frappe.web_form.set_values(res);
				}
			})
		}
	});

	// frappe.validate_phone_field(['phone_number']);
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