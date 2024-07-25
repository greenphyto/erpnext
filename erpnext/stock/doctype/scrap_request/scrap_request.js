// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Scrap Request', {
	item: function(frm) {
		update_quantity(frm)
	},
	warehouse: function(frm) {
		update_quantity(frm)
	},
	refresh: function(frm) {
		frm.set_query("batch", "items", (doc, cdt,cdn)=>{
			var d = locals[cdt][cdn];
			return {
				filters:{
					item:d.item_code
				},
				query:"erpnext.stock.doctype.scrap_request.scrap_request.get_batch_numbers"
			}
		})

		frm.set_query("warehouse", "items", (doc, cdt,cdn)=>{
			var d = locals[cdt][cdn];
			return {
				filters:{
					item:d.item_code,
					batch:d.batch
				},
				query:"erpnext.stock.doctype.scrap_request.scrap_request.get_warehouse"
			}
		})
	}
});

frappe.ui.form.on('Scrap Items', {
	item_code: function(frm,cdt,cdn){
		update_quantity(cdt,cdn)
	},
	warehouse: function(frm,cdt,cdn){
		update_quantity(cdt,cdn)
	}
})

function update_quantity(cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code && d.warehouse) {
		frappe.call({
			method: "erpnext.accounts.doctype.pos_invoice.pos_invoice.get_stock_availability",
			args: {
				'item_code': d.item_code,
				'warehouse': d.warehouse,
			},
			callback: function(r) {
				if(r.message) {
					frappe.model.set_value(cdt,cdn, "cur_qty", r.message)
				}
			}
		});
	}else{
		frappe.model.set_value(cdt,cdn, "cur_qty", 0)
	}
}