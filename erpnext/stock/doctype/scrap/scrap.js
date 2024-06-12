// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Scrap', {
	item: function(frm) {
    update_quantity(frm)
  },
	warehouse: function(frm) {
    update_quantity(frm)
  },
});

function update_quantity(frm) {
	if (frm.doc.item_code && frm.doc.warehouse) {
		frappe.call({
			method: "erpnext.accounts.doctype.pos_invoice.pos_invoice.get_stock_availability",
			args: {
				'item_code': frm.doc.item_code,
				'warehouse': frm.doc.warehouse,
			},
			callback: function(r) {
				if(r.message) {
					frm.set_value("inventory_quantity", r.message);
				}
			}
		});
	}
}
