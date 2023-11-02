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
	],
	"formatter": function(value, row, column, data, default_formatter) {
		if (value=="Button"){
			console.log("Here")
		}
		value = default_formatter(value, row, column, data);
		if (data && data.is_group) {
			value = value.bold();
			console.log(16, value)
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