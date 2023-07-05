// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Maintenance Request', {
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
	},

	create_to_do: function(frm) {
		frappe.call({
			args: {},
			method: "erpnext.smart_fm.doctype.maintenance_request.maintenance_request.create_to_do",
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	create_asset_repair: function(frm) {
		frappe.call({
			args: {
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
