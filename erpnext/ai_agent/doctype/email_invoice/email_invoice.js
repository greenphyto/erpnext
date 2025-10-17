// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Email Invoice', {
	refresh: function(frm) {
		frm.add_custom_button(__('Sync Again'), function() {
            frappe.call({
                method: "sync_from_ui",
				doc:frm.doc,
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint(__("Sync completed successfully"));
                        frm.reload_doc();
                    }
                }
            });
			frappe.show_alert("Syncing now")
        });
	}
});
