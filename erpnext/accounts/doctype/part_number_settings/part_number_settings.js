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

		frm.add_custom_button(__('Edit All'), () => {
			frappe.prompt([
				{'fieldname': 'material_group', 'fieldtype': 'Link', 'label': 'Material Group', 'reqd': 1, "options":"Material Group"},
				{'fieldname': 'account_code', 'fieldtype': 'Link', 'label': 'Account Code', 'reqd': 1, "options":"Account"}
			],
			function(r){
				$.each(frm.doc.data_mapping, (i, d)=>{
					if (r.material_group==d.material_group){
						frappe.model.set_value(d.doctype, d.name, "account_code", r.account_code);
					}
				})
			},
			'Update all account code',
			'Submit'
			)
		})
	}
});
