
frappe.ready(function() {
	setup();
	
	// refresh
	frappe.web_form.set_time_option();
	frappe.web_form.setup_preview();


	frappe.set_default_web_form([
		"email as email_address", 
		"full_name as full_name"
	])

	// bind events here
	frappe.web_form.on("service", (frm, value)=>{
		if (value){
			frappe.set_value_web_form("Facility Service", {"name":value}, [
				"available_qty as quantity_available",
				"description",
				"image as preview_link" ,
				"status as service_status"
			]).then(r=>{
				// set image service
				frappe.render_image_field("service-image", r.preview_link);
			})
		}
		
		frappe.web_form.set_time_option();
	})

	// // from_time
	frappe.web_form.on("from_date", (frm, value)=>{
		frappe.web_form.set_total_duration();
	})
	frappe.web_form.on("to_date", (frm, value)=>{
		frappe.web_form.set_total_duration();
	})
	frappe.web_form.on("start_time", (frm, value)=>{
		frappe.web_form.set_total_duration();
	})
	frappe.web_form.on("end_time", (frm, value)=>{
		frappe.web_form.set_total_duration();
	})

	// // to_time
	// frappe.web_form.on("to_time", (frm, value)=>{
	// 	frappe.web_form.set_total_duration();
	// })

	// all_day
	frappe.web_form.on("all_day", (frm, value)=>{
		frappe.web_form.setup_preview();
		frappe.web_form.setup_value();
		frappe.web_form.set_total_duration();
	})

	// repeat_data
	frappe.web_form.on("repeat_data", (frm, value)=>{
		frappe.web_form.setup_value();
		frappe.web_form.setup_preview();
		frappe.web_form.set_total_duration();

	})

	setup_repeat_button(frappe.web_form);

})

function setup(){
	frappe.provide("frappe.web_form")
	$.extend(frappe.web_form, {
		set_total_duration(){
			var me = this;
			var seconds = 0;
			if (me.doc.repeat_data){
				seconds = (moment(me.doc.to_date, 'YYYY-MM-DD') - moment(me.doc.from_date, 'YYYY-MM-DD')) / 1000 + 24 * 3600
			}else{
				seconds = (moment(me.doc.end_time, 'HH:mm') - moment(me.doc.start_time, 'HH:mm')) / 1000
			}
			if (seconds){
				me.set_value("total_duration", seconds);
			}else{
				me.set_value("total_duration", 0);
			}
		},
		setup_preview(){
			// if all day: hide time
			var me = this;
			var from_date = me.fields_dict.from_date;
			if (me.doc.all_day){
				me.set_df_property("end_time", "hidden", 1);
				me.set_df_property("start_time", "hidden", 1);
			}else{
				me.set_df_property("end_time", "hidden", 0);
				me.set_df_property("start_time", "hidden", 0);
			}
			
			// if multi days: hide time
			if (me.doc.repeat_data){
				me.set_df_property("to_date", "hidden", 0);
				from_date.df.label = "From Date";
				from_date.refresh();
			}else{
				me.set_df_property("to_date", "hidden", 1);
				from_date.df.label = "Date";
				from_date.refresh();
			}
		},
		setup_value: function(){
			var me = this;
			if (!me.doc.service) return;
	
			var time_list = me.fields_dict.start_time.df.options.split("\n");
	
			if (me.doc.all_day || me.doc.repeat_data){
				me.set_value("start_time", time_list[0]);
				me.set_value("end_time", time_list[time_list.length-1]);
				
			}
			if (!me.doc.repeat_data){
				me.set_value("to_date", me.doc.from_date);
			}
		},
		set_time_option: function(){
			var me = this;
			if(!me.doc.service){
				me.set_df_property("start_time", 'options', "");
				me.set_df_property("end_time", 'options', "");
				return;
			};
			var opts = "";
			frappe.db.get_value("Facility Service", me.doc.service, ['time_start', 'time_end', "interval"]).then(r=>{
				r = r.message;
				var temp = generateTimeList(r.time_start, r.time_end, r.interval);
				opts = temp.join("\n");
				me.set_df_property("start_time", "options", opts);
				me.set_df_property("end_time", "options", opts);
	
				setTimeout(()=>{
					if ( !in_list(temp, me.doc.start_time) ){
						me.set_value("start_time", temp[0])
					}
					if ( !in_list(temp, me.doc.end_time) ){
						me.set_value("end_time", temp[1])
					}
				}, 100)
			})
	
			function generateTimeList(time_start, time_end, interval) {
				let timeList = [];
				
				// Parsing waktu awal dan akhir
				let start = moment(time_start, 'HH:mm:ss').toDate();
				let end = moment(time_end, 'HH:mm:ss').toDate();
			
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
}

function setup_repeat_button(frm){
	var wrapper = frm.fields_dict.repeat.$wrapper;
	var btn_wrapper = $(wrapper.find(".control-input"));
	wrapper.empty().append(`<div class="btn btn-secondary btn-repeat">Repeat</div>`);
	wrapper.on("click", ".btn-repeat", ()=>{
		if (frm.doc.docstatus==0){
			open_repeat_selector(frm);
		}
	})
}


function open_repeat_selector(frm){
	var me = {
		frm:frm
	}
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
			// {label:`Custom`, value:"custom"}
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

function nthDate(date) {
	date = new Date(date);
	let nth = Math.ceil(date.getDate() / 7);
	nth = ["first", "second", "third", "fourth", "fifth"][((nth + 90) % 100 - 10) % 10 - 1];
	return `${nth}`;
  }