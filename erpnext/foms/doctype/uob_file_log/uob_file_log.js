// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('UOB File Log', {
	refresh: function(frm) {
		me.frm.add_custom_button(__('Sync Now'), function () {
				frappe.call({
					method:"sync_payment_status",
					doc:frm.doc,
					callback:(r)=>{
						frappe.show_alert({
							message:"Sync done!",
							indicator: "green"
						}, 3)
					}
				})
			});
	}
});
