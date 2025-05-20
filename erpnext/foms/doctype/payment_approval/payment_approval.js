// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Approval', {
	refresh: function(frm) {
		frm.set_query("invoice_no", "invoices", ()=>{
			return{
				filters:{
					docstatus:1,
					outstanding_amount:[">", 0]
				}
			}
		})
	},
	after_save: function(frm) {
        frm.reload_doc();
    }
});
