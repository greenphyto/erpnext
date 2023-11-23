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
		frm.cscript.set_time_option();
		frm.cscript.setup_preview();
	},
	all_day:function(frm){
		frm.cscript.setup_preview();
		frm.cscript.setup_value();
	},
	multi_days:function(frm){
		frm.cscript.setup_value();
		frm.cscript.setup_preview();
	},
	service: function(frm){
		frm.cscript.set_time_option();
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
		if (!this.frm.is_dirty() || !this.frm.doc.service) return;

		var time_list = me.frm.fields_dict.start_time.df.options.split("\n");

		if (me.frm.doc.all_day || me.frm.doc.multi_days){
			me.frm.set_value("start_time", time_list[0]);
			me.frm.set_value("end_time", time_list[time_list.length-1]);
			
		}
		if (!me.frm.doc.multi_days){
			me.frm.set_value("to_date", me.frm.doc.from_date);
		}
	},
	set_time_option: function(){
		var me = this;
		if(!me.frm.doc.service){
			me.frm.set_df_property("start_time", 'options', "");
			me.frm.set_df_property("end_time", 'options', "");
			return;
		};
		var opts = "";
		frappe.db.get_value("Facility Service", me.frm.doc.service, ['time_start', 'time_end', "interval"]).then(r=>{
			r = r.message;
			var temp = generateTimeList(r.time_start, r.time_end, r.interval);
			opts = temp.join("\n");
			me.frm.set_df_property("start_time", "options", opts);
			me.frm.set_df_property("end_time", "options", opts);

			setTimeout(()=>{
				if (me.frm.is_dirty()){
					if ( !in_list(temp, me.frm.doc.start_time) ){
						me.frm.set_value("start_time", temp[0])
					}
					if ( !in_list(temp, me.frm.doc.end_time) ){
						me.frm.set_value("end_time", temp[1])
					}
				}
			}, 100)
		})

		function generateTimeList(time_start, time_end, interval) {
			let timeList = [];
			
			// Parsing waktu awal dan akhir
			let start = new Date("1970-01-01T" + time_start);
			let end = new Date("1970-01-01T" + time_end);
		
			// Loop untuk menghasilkan waktu dengan interval tertentu
			let current = start;
			while (current <= end) {
				let formattedTime = current.getHours().toString().padStart(2, '0') + ':' + current.getMinutes().toString().padStart(2, '0');
				timeList.push(formattedTime);
		
				// Menambahkan interval ke waktu saat ini
				current.setMinutes(current.getMinutes() + cint(interval));
			}
		
			return timeList;
		}
	}
})