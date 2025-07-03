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

		frm.set_query("bank_account", ()=>{
			return{
				filters:{
					"swift_number":["like", "UOVB%"]
				}
			}
		})

		if(!frm.doc.requested_by && frm.is_dirty()){
			frm.set_value("requested_by", frappe.session.user)
		}
		frm.cscript.setup_method();
	},
	after_save: function(frm) {
		frm.reload_doc();
    },
	payment_method: function(frm){
		frm.cscript.setup_method();
	},
	payment_type: function(frm){
		frm.cscript.setup_method();
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
	setup_method(){
		var me = this.frm;
		var doc = this.frm.doc;
		var payment_method_field = me.fields_dict.payment_method;
		var payment_property_field = me.fields_dict.payment_property;
		if (doc.payment_type=="Transfer" && in_list(["IBG", "FAST"], doc.payment_method)){
			payment_property_field.df.hidden = 1
			payment_method_field.df.hidden = 0
		} else if (doc.payment_type=="Cheque"){
			payment_property_field.df.options = "CHQ\nCO"
			payment_property_field.df.hidden = 0
			payment_method_field.df.hidden = 1
		} else{
			payment_property_field.df.options = ""
			payment_property_field.df.hidden = 1
			payment_method_field.df.hidden = 0
		}
		payment_property_field.refresh()
		payment_method_field.refresh()
	},
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
