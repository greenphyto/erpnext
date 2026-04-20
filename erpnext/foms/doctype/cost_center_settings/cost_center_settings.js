// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cost Center Settings', {
	refresh: function(frm) {
		frm.add_custom_button(__('Get Items'), () => {
			if (!frm.doc.company){
				frappe.throw("Company must be set!")
			}
			frappe.call({
				method:"load_items",
				doc:frm.doc,
				callback: function(r){
					frm.refresh();
					frm.dirty();
				}
			})
		})

		frm.set_query("account", "cost_center", (doc)=>{
			return {
				filters:{
					company: doc.company
				}
			}
		})

		frm.set_query("cost_center", "cost_center", (doc)=>{
			return {
				filters:{
					company: doc.company
				}
			}
		})
	}
});
