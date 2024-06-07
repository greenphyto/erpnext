// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Permit to Work', {
	onload: function(frm) {
		frm.cscript.set_min_date(frm);
		frm.cscript.update_max_date(frm);
	},
	date_time_work_start: function(frm){
		frm.cscript.update_max_date(frm);
	}
});

frappe.provide("cur_frm.cscript");
$.extend(cur_frm.cscript, {
	set_max_date: function(frm){
		var to_field = frm.fields_dict.date_time_work_complete.custom_options = {
			maxDate: new Date("2024-06-15")
		}
	},
	set_min_date: function(frm){
		var start_field = frm.fields_dict.date_time_work_start;
		start_field.custom_options = {
			minDate: new Date()
		}
	},
	update_max_date: function(frm){
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
})