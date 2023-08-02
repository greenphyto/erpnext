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
	}
});

$.extend(cur_frm.cscript, {
	refresh_tree_view: function(){

	}
})