frappe.ready(function() {
	// bind events here
	console.log("custom JS")

	// set disable edit when submit
	var doc = frappe.web_form.doc;

	if (doc.docstatus != 0){
		$(".edit-button").hide();
	}

	var check_in_field = frappe.web_form.fields_dict.check_in_time;
	if (check_in_field){
		check_in_field.set_value(frappe.datetime.now_datetime())
	}
	var check_out_field = frappe.web_form.fields_dict.check_out_time;
	if (check_out_field){
		check_out_field.set_value(frappe.datetime.now_datetime())
	}
})