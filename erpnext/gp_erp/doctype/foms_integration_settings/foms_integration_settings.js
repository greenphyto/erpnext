// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('FOMS Integration Settings', {
	onload: function(frm){
		frappe.realtime.on("progress_foms_download", data=>{
			console.log(data)
		})

		frappe.realtime.on('foms_sync_progress', data => {
			console.log(11, data);
		});
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
	},
	get_foms_recipe: function(frm) {
		frappe.call({
			"doc": frm.doc,
			"method":"get_recipe"
		})
	},
	sync_customer: function(frm) {
		console.log("Running now..")
		frappe.call({
			"doc": frm.doc,
			"method":"sync_customer"
		})
	},
	sync_supplier: function(frm) {
		frappe.call({
			"doc": frm.doc,
			"method":"sync_supplier"
		})
	},
	sync_warehouse: function(frm) {
		frappe.call({
			"doc": frm.doc,
			"method":"sync_warehouse"
		})
	},
	sync_packaging: function(frm) {
		frappe.call({
			"doc": frm.doc,
			"method":"get_packaging"
		})
	},
	get_batch: function(frm) {
		frappe.call({
			"doc": frm.doc,
			"method":"get_batch"
		})
	},
});
