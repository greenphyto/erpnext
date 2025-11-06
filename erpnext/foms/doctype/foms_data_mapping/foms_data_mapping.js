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
				var endpoint = `erpnext.controllers.erp_api.${frm.doc.endpoint}`;
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
						print_traceback_only(err);
					}
				});
			}
		);
	},

	edit_data: function(frm){
		if (frm.doc.raw_data && frm.doc.edit_data==1){
			var data = prettyJson(frm.doc.raw_data);
			frm.set_value("raw_data", data);
		}
	}
});

function print_traceback_only(response) {
	try {
		// pastikan response dari frappe.call atau fetch().json()
		let exc_str = response.exc || response._server_messages;
		if (!exc_str) {
			console.log("No traceback available in response.");
			return;
		}

		// kadang `exc` adalah string JSON list, parse sekali lagi
		let traceback_list = [];
		try {
			traceback_list = JSON.parse(exc_str);
		} catch {
			traceback_list = [exc_str];
		}

		// print traceback (biasanya elemen pertama)
		console.group("ERROR Traceback");
		console.log(traceback_list[0]);
		console.groupEnd();
	} catch (e) {
		console.error("Error printing traceback:", e);
	}
}

function prettyJson(input) {
	try {
		// jika input masih berupa string JSON → parse dulu
		const obj = typeof input === "string" ? JSON.parse(input) : input;
		// stringify kembali dengan 4 spasi indent
		return JSON.stringify(obj, null, 4);
	} catch (e) {
		console.error("Invalid JSON:", e);
		return input; // fallback: kembalikan aslinya kalau bukan JSON valid
	}
}