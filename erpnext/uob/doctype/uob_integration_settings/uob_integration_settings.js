// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('UOB Integration Settings', {
	get_file_list: function(frm) {
		frappe.show_alert("in progres");
		frappe.call({
			method:"get_file_list",
			doc:frm.doc,
			callback:r=>{
				if (r.message && r.message.result) {
					var files = r.message.result;
					const file_rows = files.map(file => `
						<tr>
							<td>${file.name}</td>
							<td>${flt(file.size)/1000}Kb</td>
							<td>${file.modified}</td>
							<td>${file.type}</td>
							<td><a target="" href="/api/method/erpnext.uob.doctype.uob_integration_settings.uob_integration_settings.download_bank_file?fname=${file.name}&decrypt=0">Raw</a></td>
							<td><a target="" href="/api/method/erpnext.uob.doctype.uob_integration_settings.uob_integration_settings.download_bank_file?fname=${file.name}&decrypt=1">File</a></td>
						</tr>
					`).join('');

					const dialog = new frappe.ui.Dialog({
						title: 'Files on Remote Server',
						size: 'large',
						fields: [{
							fieldtype: 'HTML',
							fieldname: 'file_list_html',
							options: `
								<table class="table table-bordered table-striped">
									<thead>
										<tr>
											<th>File Name</th>
											<th>Size</th>
											<th>Modified</th>
											<th>Type</th>
											<th colspan="2">Download</th>
										</tr>
									</thead>
									<tbody>${file_rows}</tbody>
								</table>
							`
						}],
					});

					dialog.show();
				}
			}
		})
	}
});