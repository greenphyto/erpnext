// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('FOMS Integration Settings', {
	onload: function(frm){
		frappe.realtime.on("progress_foms_download", data=>{
			console.log(data)
		})
	},
	get_foms_raw_material: function(frm) {
		frappe.call({
			"doc": frm.doc,
			"method":"get_raw_material"
		})
	},
	get_foms_products: function(frm) {
		frappe.call({
			"doc": frm.doc,
			"method":"get_products"
		})
	}	
});
