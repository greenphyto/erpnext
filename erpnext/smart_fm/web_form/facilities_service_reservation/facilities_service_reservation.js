console.log("here form")

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
	console.log("here form")
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
	})

	// multi_days
	frappe.web_form.on("multi_days", (frm, value)=>{
		frappe.web_form.setup_value();
		frappe.web_form.setup_preview();
	})

})


function setup(){
	frappe.provide("frappe.web_form")
	$.extend(frappe.web_form, {
		set_total_duration(){
			var me = this;
			var seconds = 0;
			if (me.doc.multi_days){
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
			if (me.doc.all_day || me.doc.multi_days){
				me.set_df_property("end_time", "hidden", 1);
				me.set_df_property("start_time", "hidden", 1);
			}else{
				me.set_df_property("end_time", "hidden", 0);
				me.set_df_property("start_time", "hidden", 0);
			}
			
			// if multi days: hide time
			if (me.doc.multi_days){
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
	
			if (me.doc.all_day || me.doc.multi_days){
				me.set_value("start_time", time_list[0]);
				me.set_value("end_time", time_list[time_list.length-1]);
				
			}
			if (!me.doc.multi_days){
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