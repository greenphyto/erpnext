// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Scrap Request', {
	refresh: function(frm) {
		frm.set_query("batch", "items", (doc, cdt,cdn)=>{
			var d = locals[cdt][cdn];

			if (!d.item_code){
				frappe.throw(__("Please select Item."))
			}
			return {
				filters:{
					item:d.item_code
				},
				query:"erpnext.stock.doctype.scrap_request.scrap_request.get_batch_numbers"
			}
		})
	}
});

frappe.ui.form.on('Scrap Items', {
	item_code: function(frm,cdt,cdn){
		frappe.model.set_value(cdt,cdn, "batch", "");
		frappe.model.set_value(cdt,cdn, "cur_qty", "");
		frappe.model.set_value(cdt,cdn, "uom", "");
	}
})