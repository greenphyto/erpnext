frappe.ui.form.on('Process Statement Of Accounts', {
	start: function(frm) {
		if (frm.doc.report == "General Ledger") {
			if (frm.doc.from_date && frm.doc.to_date && frm.doc.company) {
				var url = "/api/method/erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts.get_report_pdf?doc=" + encodeURIComponent(JSON.stringify(frm.doc)) + "&report=" + frm.doc.report + "&Naming_Series=" + frm.doc.naming_series + "&from_date=" + frm.doc.from_date + "&to_date=" + frm.doc.to_date;

				function download_now() {
					$.ajax({
						url: url,
						type: 'GET',
						success: function(result) {
							if (jQuery.isEmptyObject(result)) {
								frappe.msgprint(__('No Records for these settings.'));
							} else {
								window.location = url;
							}
						}
					});
				}

				if (frm.is_dirty()) {
					frm.save().then(() => {
						download_now();
					});
				} else {
					download_now();
				}
			}
		}
	},
});
