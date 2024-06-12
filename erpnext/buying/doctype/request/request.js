// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Request', {
	quantity: function(frm) {
    update_weight(frm)
  },
	packaging_size: function(frm) {
    update_weight(frm)
  },
});

function update_weight(frm) {
	frm.set_value("weight", flt(frm.doc.quantity * frm.doc.packaging_size));
}