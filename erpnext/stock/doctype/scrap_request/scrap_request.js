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
		frm.set_query("item_code", "items", (doc, cdt,cdn)=>{
			return {
				filters:{
					is_stock_item:1,
					is_fixed_asset:0
				}
			}
		})
	}
});

frappe.ui.form.on('Scrap Items', {
	item_code: function(frm,cdt,cdn){
		frappe.model.set_value(cdt,cdn, "batch", "");
		frappe.model.set_value(cdt,cdn, "cur_qty", "");
		frappe.model.set_value(cdt,cdn, "uom", "");
		frm.cscript.add_expense_account(frm, cdt, cdn);
	}
})

$.extend(cur_frm.cscript, {
	add_expense_account: function(frm,cdt,cdn){
		var d = locals[cdt][cdn];
		if(d.item_code && frm.doc.company){
			frappe.call({
				method:"erpnext.stock.doctype.stock_entry.stock_entry.get_item_expense_for_issue",
				args: {
					company:frm.doc.company,
					item_code:d.item_code
				},
				callback: (r)=>{
					frappe.model.set_value(cdt, cdn, "expense_account", r.message);
				}
			})
		}else{
			frappe.model.set_value(cdt, cdn, "expense_account", "");
		}
		
	}
})