// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on('Budget', {
	onload: function(frm) {
		frm.set_query("account", "accounts", function() {
			return {
				filters: {
					company: frm.doc.company,
					report_type: "Profit and Loss",
					is_group: 0
				}
			};
		});

		frm.set_query("monthly_distribution", function() {
			return {
				filters: {
					fiscal_year: frm.doc.fiscal_year
				}
			};
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	refresh: function(frm) {
		frm.trigger("toggle_reqd_fields");
		
		// Add Upload Budget Template button
		if (!frm.is_new()) {
			frm.add_custom_button(__('Upload Budget Template'), function() {
				frm.trigger('show_upload_dialog');
			});
		}
	},

	show_upload_dialog: function(frm) {
		const d = new frappe.ui.Dialog({
			title: __('Upload Budget Template'),
			fields: [
				{
					fieldtype: 'HTML',
					fieldname: 'download_section',
					options: `
						<div class="form-group">
							<div class="clearfix">
								<label class="control-label" style="padding-right: 0px;">Download Template</label>
							</div>
							<button class="btn btn-default btn-sm" id="btn-download-budget-template">
								<i class="fa fa-download"></i> Download Excel Template
							</button>
							<p class="help-box small text-muted">
								Download the Excel template with the format: Cost Center | Account | January - December
							</p>
						</div>
					`
				},
				{
					fieldname: 'upload_file',
					fieldtype: 'Attach',
					label: __('Select Excel File'),
					reqd: 1,
					options: {
						restrictions: {
							allowed_file_types: ['.xlsx', '.xls', '.csv']
						}
					}
				},
				{
					fieldtype: 'HTML',
					fieldname: 'help_text',
					options: `
						<div class="alert alert-info">
							<strong>Template Format:</strong><br>
							Excel file should contain columns:<br>
							<strong>Cost Center | Account | January | February | March | ... | December</strong><br>
							<small>Total Budget Amount will be calculated automatically from the sum of all months.</small>
						</div>
					`
				}
			],
			primary_action_label: __('Upload & Process'),
			primary_action: function(values) {
				if (!values.upload_file) {
					frappe.msgprint(__('Please select a file to upload'));
					return;
				}
				
				frappe.show_alert({
					message: __('Processing file...'),
					indicator: 'blue'
				}, 3);

				frappe.call({
					method: 'erpnext.accounts.doctype.budget.budget.upload_budget_template',
					args: {
						docname: frm.doc.name,
						file_url: values.upload_file
					},
					freeze: true,
					freeze_message: __('Processing Budget Template...'),
					callback: function(r) {
						if (r.message) {
							d.hide();
							frappe.show_alert({
								message: __('Budget data imported successfully!'),
								indicator: 'green'
							}, 5);
							frm.reload_doc();
						}
					},
					error: function(r) {
						frappe.msgprint({
							title: __('Upload Failed'),
							message: r.message || __('An error occurred while processing the file'),
							indicator: 'red'
						});
					}
				});
			}
		});
		
		d.show();
		
		// Attach click event to download button after dialog is shown
		d.$wrapper.find('#btn-download-budget-template').on('click', function() {
			window.open(
				'/api/method/erpnext.accounts.doctype.budget.budget_upload_template.download_budget_template?company=' 
				+ encodeURIComponent(frm.doc.company)
			);
		});
	},

	budget_against: function(frm) {
		frm.trigger("set_null_value")
		frm.trigger("toggle_reqd_fields")
	},

	set_null_value: function(frm) {
		if(frm.doc.budget_against == 'Cost Center') {
			frm.set_value('project', null)
		} else {
			frm.set_value('cost_center', null)
		}
	},

	toggle_reqd_fields: function(frm) {
		frm.toggle_reqd("cost_center", frm.doc.budget_against=="Cost Center");
		frm.toggle_reqd("project", frm.doc.budget_against=="Project");
	}
});
