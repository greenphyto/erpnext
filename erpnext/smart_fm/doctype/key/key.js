// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Key', {
	// refresh: function(frm) {

	// }

  get_key: function(frm) {
    frappe.call({
      method: "erpnext.smart_fm.doctype.key.key.get_key",
			args: {
				"name": frm.doc.name,
				"room": frm.doc.room,
      },
      callback: function(r) {
        var events = me.prepare_events(r.message);
        callback( events )
      }
    });
  },
});
