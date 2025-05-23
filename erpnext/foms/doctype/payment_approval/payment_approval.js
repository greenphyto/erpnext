// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Approval', {
	refresh: function(frm) {
		frm.set_query("invoice_no", "invoices", ()=>{
			return{
				filters:{
					docstatus:1,
					outstanding_amount:[">", 0]
				}
			}
		})

		frm.set_query("supplier_bank_no", "invoices", (doc, cdt, cdn)=>{
			var d = locals[cdt][cdn]
			return{
				filters:{
					party: d.party,
					party_type:"Supplier"
				}
			}
		})
	},
	after_save: function(frm) {
        frm.reload_doc();
    },
	before_workflow_action: function(frm){
		return new Promise((resolve, reject) => {
			frm.cscript.reject_payment_approval().then((r)=>{
				if (r){
					resolve()
				}
			});
		})
	}
})

$.extend(cur_frm.cscript, {
	reject_payment_approval(){
		return new Promise((resolve) => {
			var me = this;
			if (me.frm.selected_workflow_action == "Reject"){
				var d = new frappe.ui.Dialog({
					title: __('Reason for Reject'),
					fields: [
						{
							"fieldname": "reason",
							"fieldtype": "Small Text",
							"label": "Reason:",
							"reqd": 1,
						}
					],
					primary_action: function() {
						var data = d.get_values();
						let reason = 'Reason for Reject: ' + data.reason;
		
						frappe.call({
							method: "frappe.desk.form.utils.add_comment",
							args: {
								reference_doctype: me.frm.doctype,
								reference_name: me.frm.docname,
								content: __(reason),
								comment_email: frappe.session.user,
								comment_by: frappe.session.user_fullname
							},
							callback: function(r) {
								me.frm.reload_doc()
								d.finish = true;
								d.hide();
							}
						});
					},
					onhide:()=>{
						if (d.finish){
							resolve(true);
						}else{
							resolve(false);
						}
					}
				});
				d.show();
			}else{
				resolve(true);
			}
		})
	}
})
