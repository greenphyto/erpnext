frappe.ready(function() {
	// bind events here

	frappe.web_form.on("date_time_work_start", (frm, value)=>{
		frappe.update_max_date(frappe.web_form);
	});

	var doc = frappe.web_form.doc;

	if (doc.docstatus == 2){
		$(".edit-button").hide();
	}

	frappe.web_form.on("attachment", (frm, value)=>{
		frappe.web_form.set_df_property("attachment2", "hidden", 0)
	});

	frappe.web_form.on("attachment2", (frm, value)=>{
		frappe.web_form.set_df_property("attachment3", "hidden", 0)
	});

	frappe.web_form.on("attachment3", (frm, value)=>{
		frappe.web_form.set_df_property("attachment4", "hidden", 0)
	});

	// init
	var doc = frappe.web_form.doc;
	frappe.web_form.set_df_property("attachment2", "hidden", !doc.attachment ? 1 : 0 );
	frappe.web_form.set_df_property("attachment3", "hidden", !doc.attachment2 ? 1 : 0 );
	frappe.web_form.set_df_property("attachment4", "hidden", !doc.attachment3 ? 1 : 0 );

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