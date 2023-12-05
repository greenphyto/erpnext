// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Firebase Notification Settings', {
	test_send: function(frm) {
		frm.cscript.test_notif();
	}
});

frappe.provide("cur_frm.cscript")
$.extend(cur_frm.cscript, {
	test_notif: function(frm){
		if (!this.dialog_test_notif){
			this.dialog_test_notif = new frappe.ui.Dialog({
				title: 'Test Firebase Message',
				fields: [
					{
						label: 'To User',
						fieldname: 'user',
						fieldtype: 'Link',
						options: 'User',
						reqd:1
					},
					{
						label: 'Message',
						fieldname: 'message',
						fieldtype: 'Small Text'
					}
				],
				size: 'small',
				primary_action_label: 'Send',
				primary_action(val) {
					if (!val.user){
						frappe.throw("User must be set!")
						return
					}
					frappe.call({
						method:"erpnext.smart_fm.doctype.firebase_notification_settings.firebase_notification_settings.send_message",
						args:{
							message: val.message,
							user: val.user
						},
						callback: r=>{
							if (r.message){
								frappe.show_alert("Send succcess!", 3)
							}else{
								frappe.throw(`Missing token for <b>${val.user}</b>`)
							}
						}
					})
				}
			});
		}

		this.dialog_test_notif.show()
	}
})
