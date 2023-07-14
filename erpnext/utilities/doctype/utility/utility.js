// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Utility', {
	refresh: function(frm) {
    if (!frm.is_new()) {
			frm.add_custom_button(__("Meter Reading"), function() {
				frm.trigger("create_meter_reading");
			}, __("Create"));
    }
	},

  create_meter_reading: function(frm) {
    frappe.call({
      args: {
        "name": frm.doc.name,
        "location": frm.doc.meter_location,
      },
      method: "erpnext.utilities.doctype.utility.utility.create_meter_reading",
      callback: function(r) {
        var doclist = frappe.model.sync(r.message);
        frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
      }
    });
  },
});
