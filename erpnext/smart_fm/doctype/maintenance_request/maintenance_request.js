// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// don't delete this!
// {% include "erpnext/public/js/controllers/request_doc.js" %}

frappe.ui.form.on('Maintenance Request', {
  onload: function (frm) {
    frappe.db.get_value("User", frappe.session.user, ["email", "full_name", "phone", "mobile_no"])
    .then(r => {
      let values = r.message;
      frm.set_value("name1", values.full_name);
      frm.set_value("email_address", values.email);
      frm.set_value("phone_number", values.phone);
    });
  },
  
	refresh: function(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("ToDo"), function() {
				frm.trigger("create_to_do");
			}, __("Create"));
			frm.add_custom_button(__("Asset Repair"), function() {
						frm.trigger("create_asset_repair");
			}, __("Create"));
			frm.add_custom_button(__("Asset Maintenance Log"), function() {
						frm.trigger("create_asset_maintenance_log");
			}, __("Create"));
		}
		frm.events.set_default_value(frm);
	},

	create_to_do: function(frm) {
		frappe.call({
			args: {
				"name": frm.doc.name,
      },
			method: "erpnext.smart_fm.doctype.maintenance_request.maintenance_request.create_to_do",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	set_default_value: function(frm){
		if(frm.is_new() && frm.is_dirty()){
			frm.set_value("datetime", frappe.datetime.now_datetime());
		}
	},

	create_asset_repair: function(frm) {
		frappe.call({
			args: {
				"name": frm.doc.name,
				"asset": frm.doc.asset ?? null,
				"asset_name": frm.doc.asset_name ?? null
			},
			method: "erpnext.smart_fm.doctype.maintenance_request.maintenance_request.create_asset_repair",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	create_asset_maintenance_log: function(frm) {
		frappe.call({
			args: {
				"name": frm.doc.name ?? null,
				"asset_name": frm.doc.asset_name ?? null,
				"item_code": frm.doc.item_code ?? null,
				"item_name": frm.doc.item_name ?? null,
			},
			method: "erpnext.smart_fm.doctype.maintenance_request.maintenance_request.create_asset_maintenance_log",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		})
	},
});
