// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cleaning and Security Checklist', {
	refresh: function(frm) {
		if (frm.is_new()){
			frm.set_value("pic", frappe.session.user);
		}

		// filter enable template only
		frm.set_query("template", ()=>{
			return {
				filters:{
					enable: 1
				}
			}
		})
	},
	template: function(frm){
		frm.cscript.load_template()
	}
});

$.extend(cur_frm.cscript, {
	load_template: function(){
		if (!this.frm.doc.template){
			return;
		};

		frappe.call({
			method:"load_template_indicator",
			doc: this.frm.doc,
			callback: function(){
				cur_frm.refresh();
			}
		})
	}
})