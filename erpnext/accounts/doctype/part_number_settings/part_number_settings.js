// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Part Number Settings', {
	refresh: function(frm) {
		frm.add_custom_button(__('Get Items'), () => {
			frappe.call({
				method:"load_items",
				doc:frm.doc,
				callback: function(r){
					frm.refresh();
					frm.dirty();
				}
			})
		})
	}
});
