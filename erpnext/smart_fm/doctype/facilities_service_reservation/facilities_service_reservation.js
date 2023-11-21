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
	},
	refresh: function(frm){
		frm.cscript.setup_preview();
	},
	all_day:function(frm){
		frm.cscript.setup_preview();
		frm.cscript.setup_value();
	},
	multi_days:function(frm){
		frm.cscript.setup_value();
		frm.cscript.setup_preview();
	}
});

var START_TIME = '09:00';
var END_TIME = '18:00';

frappe.provide("cur_frm.cscript")
$.extend(cur_frm.cscript, {
	set_total_duration(){
		var frm = this.frm;
		var seconds = (moment(frm.doc.to_time) - moment(frm.doc.from_time)) /1000
		frm.set_value("total_duration", seconds);
	},
	setup_preview(){
		// if all day: hide time
		var me = this;
		var from_date = me.frm.fields_dict.from_date;
		var to_date = me.frm.fields_dict.to_date;
		var from_time = me.frm.fields_dict.from_time;
		var to_time = me.frm.fields_dict.to_time;
		if (me.frm.doc.all_day || me.frm.doc.multi_days){
			me.frm.set_df_property("end_time", "hidden", 1);
			me.frm.set_df_property("start_time", "hidden", 1);
		}else{
			me.frm.set_df_property("end_time", "hidden", 0);
			me.frm.set_df_property("start_time", "hidden", 0);
		}
		
		// if multi days: hide time
		if (me.frm.doc.multi_days){
			me.frm.set_df_property("to_date", "hidden", 0);
			from_date.df.label = "From Date";
			from_date.refresh();
		}else{
			me.frm.set_df_property("to_date", "hidden", 1);
			from_date.df.label = "Date";
			from_date.refresh();
		}
	},
	setup_value: function(){
		var me = this;
		if (!this.frm.is_dirty()) return;

		if (me.frm.doc.all_day || me.frm.doc.multi_days){
			me.frm.set_value("start_time", START_TIME);
			me.frm.set_value("end_time", END_TIME);
			
		}
		if (me.frm.doc.all_day && !me.frm.doc.multi_days){
			me.frm.set_value("to_date", me.frm.doc.from_date);
		}
	}
})