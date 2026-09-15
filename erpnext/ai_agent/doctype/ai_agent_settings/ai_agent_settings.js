// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('AI Agent Settings', {
	// refresh: function(frm) {

	// }
	go_to_er: function(frm){
		frappe.set_route('Form', 'Scheduled Job Type', 'erp.read_email_inbox');
	},
	go_to_es: function(frm){
		frappe.set_route('Form', 'Scheduled Job Type', 'email_account.resync_email_inbox');
	},
	mark_complete_er: function(frm){
		frappe.call({
			method:"mark_complete",
			doc: frm.doc,
			args:{
				typ:2
			},
			callback: function(){
				frm.reload_doc()
			}
		})
	},
	mark_complete_es: function(frm){
		frappe.call({
			method:"mark_complete",
			doc: frm.doc,
			args:{
				typ:1
			},
			callback: function(){
				frm.reload_doc()
			}
		})
	}
});
