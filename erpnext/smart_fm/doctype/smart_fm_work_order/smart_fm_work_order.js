// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Smart FM Work Order', {
	refresh: function(frm) {
	  if (!frm.is_new()) {
		frm.add_custom_button(__("ToDo"), function() {
		  frm.trigger("create_to_do");
		}, __("Create"));
	  }
	},
  
	create_to_do: function(frm) {
	  frappe.call({
			  args: {
				  "name": frm.doc.name,
		},
		method: "erpnext.smart_fm.doctype.smart_fm_work_order.smart_fm_work_order.create_to_do",
		callback: function(r) {
		  var doclist = frappe.model.sync(r.message);
		  frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	  });
	},
  });
