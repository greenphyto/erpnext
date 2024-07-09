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
	from_date: function(frm){
		// warn changed
		if (frm.doc.repeat_data && !frm.do_not_reset_repeat_on){
			if (!['daily', 'every_weekday'].includes(frm.doc.repeat_data)){
				frappe.show_alert({
					"message":"Repeat on removed",
					"indicator": "red"
				}, 4);
				frm.set_value("repeat_data", "");
				frm.set_value("repeat_on", "");
			}
		};
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
	service: function(frm){
		frm.cscript.set_time_option();
	},
	repeat: function(frm){

		frm.cscript.open_repeat_selector();
	},
	repeat_data:function(frm){
		frm.cscript.setup_value();
		frm.cscript.setup_preview();
	},
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
		if (me.frm.doc.all_day){
			me.frm.set_df_property("end_time", "hidden", 1);
			me.frm.set_df_property("start_time", "hidden", 1);
		}else{
			me.frm.set_df_property("end_time", "hidden", 0);
			me.frm.set_df_property("start_time", "hidden", 0);
		}
		
		// if multi days: hide time
		if (me.frm.doc.repeat_data){
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

		if (me.frm.doc.all_day || me.frm.doc.repeat_data){
			me.frm.set_value("start_time", time_list[0]);
			me.frm.set_value("end_time", time_list[time_list.length-1]);
			
		}
		if (!me.frm.doc.repeat_data){
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
			let start = moment("1970-01-01 " + time_start).toDate();
			let end = moment("1970-01-01 " + time_end).toDate();
		
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
	},
	open_repeat_selector: function(){
		/**
		 * repeat data = {
		 * 		repeat_on:"",
		 * 		days:[monday, sunday], // repeat on selected day name
		 * 		months:[january], // repeat on selected month name
		 * 		day_repeat: 1 // day count to repeat, each day, each 3 days etc
		 * 		month_repeat: 1 // month count to repeat, each month, each 3 month, etc
		 * 		special: {
		 * 			daily: true/false // repeat daily 
		 * 			weekly_on_day_name: "Friday" // repeat weekly on selected day name
		 * 			monthly_on_nth_day: "3 Friday" // repeat monthly on 1st, 2nd, etc day name
		 * 			anually_on_month_date: "July 2" // repeat annually on month-date selected
		 * 			every_weekday: true/false // only for weekday monday-friday 
		 * 		}
		 * }
		 * 
		 */
		var me = this;
		var use_date, day_no, day_name, nth_day, date_name;
		function get_options(date){
			use_date = date;
			day_no = new Date(use_date).getDay();
			day_name = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][day_no];
			nth_day = nthDate(use_date);
			date_name = moment(use_date).format("MMMM D");

			return [
				{label:"Does not repeat", 	value:"no_repeat"},
				{label:"Daily", 			value:"daily"},
				{label:`Weekly on ${day_name}`, value:`weekly_on_day_name:${day_name}`},
				{label:`Monthly on the ${nth_day} ${day_name}`, value:`monthly_on_nth_day:${nth_day}:${day_name}`},
				{label:`Annually on ${date_name}`, value:`anually_on_month_date:${date_name}`},
				{label:`Every weekday (Monday to Friday)`, value:"every_weekday"},
				{label:`Custom`, value:"custom"}
			]
		}

		function get_cur_default(opts){
			var cur_select = me.frm.doc.repeat_data;
			if (!cur_select) return "no_repeat";

			var def = $.map(opts, r=>{ if (r.value==me.frm.doc.repeat_data) return r.value})[0] || "no_repeat";

			return def;
		}

		var cur_date = me.frm.doc.from_date;
		var to_date = me.frm.doc.to_date;
		var opts = get_options(cur_date);
		var d = new frappe.ui.Dialog({
			title: __('Select schedule'),
			fields: [
				{
					"label" : "From Date",
					"fieldname": "date",
					"fieldtype": "Date",
					"reqd": 1,
					"default": cur_date,
					"onchange": function(){
						var date = d.get_value("date");
						// change options
						opts = get_options(date);
						d.set_df_property("repeat_on", "options", opts);
					}
				},
				{
					"fieldname": "column_break_ymsww",
					"fieldtype": "Column Break"
				},
				{
					"label" : "To Date",
					"fieldname": "to_date",
					"fieldtype": "Date",
					"reqd": 1,
					"default": to_date
				},
				{
					"fieldname": "section_break_a46we",
					"fieldtype": "Section Break",
				},
				{
					"label" : "Repeat on",
					"fieldname": "repeat_on",
					"fieldtype": "Select",
					"reqd": 1,
					"default": get_cur_default(opts),
					"options": opts
				},
			],
			primary_action: function() {
				var data = d.get_values();
				me.frm.do_not_reset_repeat_on = 1;
				me.frm.set_value("from_date", data.date);
				me.frm.set_value("to_date", data.to_date);
				if (data.repeat_on=="no_repeat"){
					me.frm.set_value("repeat_data", "");
					me.frm.set_value("repeat_on", "");
				}else{
					me.frm.set_value("repeat_data", data.repeat_on);
					var label = $.map(opts, r=>{ if (r.value==data.repeat_on) return r.label})[0] || "";
					me.frm.set_value("repeat_on", label);
					setTimeout(()=>{
						me.frm.do_not_reset_repeat_on = 0;
					}, 200);
				}

				d.hide();
			},
			primary_action_label: __('Submit')
		})
		d.show();
	}
})

function nthDate(date) {
	date = new Date(date);
	let nth = Math.ceil(date.getDate() / 7);
	nth = ["first", "second", "third", "fourth", "fifth"][((nth + 90) % 100 - 10) % 10 - 1];
	return `${nth}`;
  }