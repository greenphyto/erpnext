// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('FOMS Data Mapping', {
	refresh: function(frm) {
		frm.add_custom_button(__('Sync Data'), function() {
			frm.events.sync_data(frm);
		});
	},

	view_in_console: function(frm) {
		try {
			console.log(JSON.parse(frm.doc.raw_data));
			frappe.show_alert({message: __("Plot to console"), indicator: "green"});
		} catch (e) {
			frappe.msgprint(__("Invalid JSON in raw_data"));
		}
	},

	sync_data: function(frm) {

		frappe.confirm(
			'Are you sure you want to sync data?',
			() => {
				var text = frm.doc.data_name;
				var endpoint = "";
				if (/Operation\s*\d+/i.test(text)) {
					endpoint = "erpnext.controllers.erp_api.update_work_order_operation_status";
				} else if (/Finish\s*Work\s*Order/i.test(text)) {
					endpoint = "erpnext.controllers.erp_api.submit_work_order_finish_goods";
				}
				frappe.call({
					method: endpoint,
					args: JSON.parse(frm.doc.raw_data),
					callback: function(r) {
						if (!r.exc) {
							frappe.show_alert({
								message: __("Sync completed successfully"),
								indicator: "green"
							});
							console.log("Sync result:", r.message);
						} else {
							frappe.msgprint(__("Error during sync: ") + r.exc);
						}
						frm.reload_doc()
					},
					error: function(err) {
						frappe.msgprint(__("Failed to call API. See console for details."));
						console.error(err);
					}
				});
			}
		);
	}
});
