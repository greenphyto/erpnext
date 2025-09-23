// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('MinIO Backup Settings', {
	take_backup_now: function(frm) {
		frappe.call({
			"method":"erpnext.smart_fm.doctype.minio_backup_settings.minio_backup_settings.upload_backup",
			"callback":()=>{
				frappe.msgprint("Done upload");
			}
		})
	}
});
