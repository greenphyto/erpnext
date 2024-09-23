// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Material Group', {
	refresh: function(frm) {
		var fields = ['material_type', 'material_group_name', 'number_start', 'number_end'];
		var read_only = frm.doc.__onload.exist_transaction? 1 : 0;
		fields.forEach(field=>{
			frm.set_df_property(field, 'read_only', read_only);
		})

		if (read_only){
			frm.$wrapper.find(".form-message")
			.removeClass("hidden")
			.text("This document become read only when any existing items using this material group")
			.css({"background-color":"#fff6e9"})
		}
	}
});
