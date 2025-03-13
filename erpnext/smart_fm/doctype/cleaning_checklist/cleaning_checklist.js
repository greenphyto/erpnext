// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cleaning Checklist', {
	level_1_enable: function(frm){
		frm.cscript.load_area(frm,1);
	},
	level_2_enable: function(frm){
		frm.cscript.load_area(frm,2);
	},
	level_3_enable: function(frm){
		frm.cscript.load_area(frm,3);
	},
	level_4_enable: function(frm){
		frm.cscript.load_area(frm,4);
	},
	level_5_enable: function(frm){
		frm.cscript.load_area(frm,5);
	},
});

$.extend(cur_frm.cscript, {
	load_area: function(frm,level){
		frappe.call({
			method:"load_area",
			doc:frm.doc,
			args:{
				level:level
			},
			callback: function(){
				frm.refresh()
			}
		})
	}
})