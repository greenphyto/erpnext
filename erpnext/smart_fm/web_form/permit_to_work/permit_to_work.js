frappe.ready(function() {
	// bind events here

	frappe.web_form.on("date_time_work_start", (frm, value)=>{
		frappe.update_max_date(frappe.web_form);
	});

	var doc = frappe.web_form.doc;

	if (doc.docstatus == 2){
		$(".edit-button").hide();
	}

	if (frappe.web_form.in_edit_mode){
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
	}
})

frappe.update_max_date = function(frm){
	var to_field = frm.fields_dict.date_time_work_complete;
	var start_date = new Date(frm.doc.date_time_work_start || new Date());
	var cur_comp_date = to_field.get_value();
	var max_allowed_days = 7;
	var max_date = moment(start_date).add(max_allowed_days, 'days').toDate();

	if (!cur_comp_date || new Date(cur_comp_date)<start_date || new Date(cur_comp_date)>max_date){
		frm.set_value("date_time_work_complete", "");
	}

	if (!to_field.datepicker){
		to_field.custom_options = {
			maxDate: max_date,
			minDate: start_date
		}
	}else{
		to_field.datepicker.destroy();
		to_field.datepicker_options.maxDate = max_date;
		to_field.datepicker_options.minDate = start_date;
		to_field.set_datepicker();
	}
}