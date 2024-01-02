// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Building Environment Feedback Summary"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": "Date From",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": "Date To",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "filter_chart",
			"fieldtype": "Select",
			"label": "Filter Chart",
			"default": "",
			"options":[
				{"value":"q1", "label":"1. How would you rate the overall temperature comfort in the building?"},
				{"value":"q2", "label":"2. Are there areas in the building where you experience drafts or uneven temperatures?"},
				{"value":"q3", "label":"3. How satisfied are you with the natural and artificial lighting in your workspace?"},
				{"value":"q4", "label":"4. Are there any areas where you find the lighting too dim or too bright?"},
				{"value":"q5", "label":"5. How would you rate the noise level in the building?"},
				{"value":"q6", "label":"6. Are there specific sources of noise or areas in the building that are particularly disruptive?"},
				{"value":"q7", "label":"7. How would you rate the building's overall air quality and freshness?"},
				{"value":"q8", "label":"8. Do you notice any unpleasant odors or smells within the building?"},
				{"value":"q9", "label":"9. How would you describe the spaciousness of your workspace and common areas?"},
				{"value":"q10", "label":"10. Are there any areas in the building where you feel enhancements could improve your overall comfort?"},
			]
		},
		{
			"fieldname": "from_dashboard",
			"fieldtype": "Check",
			"label": "From Dashboard",
			"default": 0
		}
	],
	onload: function(report){
		// hide filters
		if ($(cur_page.page).attr("data-page-route") == 'query-report'){
			var df = report.get_filter("from_dashboard");
			df.df.hidden=1
			df.refresh();
		}
	}, 
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.is_group) {
			value = value.bold();
		}
		if (value=="Button"){
			return `<div>
				<a 
					msg_field="${data.msg_field}"
					onClick="frappe.report_script.show_messages(this);" 
					style="font-size: 0.82em;color: #a5a5a5;"
				>Show Message</a>
			</div>`
		}
		return value;
	},
};

frappe.provide("frappe.report_script")
frappe.report_script = {
	show_messages:function(el){
		var msg_field = $(el).attr("msg_field");
		var d = new frappe.ui.Dialog({
			title: 'Messages List',
			fields: [
				{
					fieldname: 'ht',
					fieldtype: 'HTML'
				}
			],
		});
		d.show();
		var main = d.fields_dict.ht.$wrapper;
		var heading = $(`<div class='msg-list-header'>Total count <span class="total">0</span> messages</div>`);
		var wrapper = $("<div class='msg-list-wrapper'></div>");
		main
		.append(heading)
		.append(wrapper);
		var filters = frappe.query_report.get_filter_values();

		// get data
		frappe.call({
			method:"erpnext.smart_fm.report.building_environment_feedback_summary.building_environment_feedback_summary.get_message_list",
			args:{
				filters:filters,
				field: msg_field
			},
			callback:function(res){
				heading.find(".total").text(res.message.total);
				$.each(res.message.messages, (i,r)=>{
					var msg_wrapper = $(`
					<div class='message-list-card'>
						<div class="body-section">
							<div class="content"></div>
						</div>
						<div class="bottom-section">
							From <span class="sender"></span>, <span class="email"></span>
						</div>
					<div>`)
					msg_wrapper.find(".content").text(r.text || "-");
					msg_wrapper.find(".sender").text(r.full_name || "-");
					msg_wrapper.find(".email").text(r.email_address || "-");
					
					wrapper.append(msg_wrapper);
				})
			}
		})
		// plot to html

		console.log("show", wrapper, msg_field)
	}
}