frappe.ui.form.on('Asset', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1) {
			if (frm.doc.disabled == 0) {
				frm.add_custom_button(__('Disable Asset'), function () {
					erpnext.disable_asset(frm, 1);
				}, "Manage");
			} else {
				frm.add_custom_button(__('Enable Asset'), function () {
					erpnext.disable_asset(frm);
				}, "Manage");
			}
		}
	},

	make_sales_invoice: function(frm) {
		frappe.call({
			method: "erpnext.assets.doctype.asset.depreciation.check_unposted_depr_before_disposal",
			args: {
				asset_name: frm.doc.name
			},
			callback: function(r) {
				var create_si = function() {
					frappe.call({
						args: {
							"asset": frm.doc.name,
							"item_code": frm.doc.item_code,
							"company": frm.doc.company,
							"serial_no": frm.doc.serial_no
						},
						method: "erpnext.assets.doctype.asset.asset.make_sales_invoice",
						callback: function(r) {
							var doclist = frappe.model.sync(r.message);
							frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
						}
					});
				};
				if (r.message && r.message.unposted_count > 0) {
					frappe.confirm(
						__("There are {0} unposted depreciation entry/entries on or before {1}. Only posted entries will be recognized when the invoice is submitted. Continue?", [
							r.message.unposted_count, r.message.disposal_date
						]),
						create_si
					);
				} else {
					create_si();
				}
			}
		});
	},
});

frappe.ui.form.on('Asset Finance Book', {
	depreciation_start_date: function(frm, cdt, cdn) {
		// GP: disabled depreciation_start_date == available_for_use_date check
	}
});

frappe.ui.form.on('Depreciation Schedule', {
	make_depreciation_entry: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row.journal_entry) {
			frappe.call({
				method: "erpnext.assets.doctype.asset.depreciation.make_depreciation_entry",
				args: {
					"assets": [frm.doc.name],
					"date": row.schedule_date
				},
				callback: function(r) {
					frm.reload_doc();
				}
			})
		}
	}
})

erpnext.disable_asset = function(frm, disabled) {
	function update_now(reason, disabled) {
		frappe.call({
			method: "erpnext.assets.doctype.asset.asset.disable_asset",
			args: {
				disable: disabled,
				asset_name: frm.doc.name,
				reason: reason
			},
			callback: function(r) {
				frm.reload_doc();
				d.hide();
			}
		});
	}
	if (disabled == 1) {
		var d = new frappe.ui.Dialog({
			title: __('Disable reason'),
			fields: [
				{
					"fieldname": "reason",
					"fieldtype": "Small Text",
					"label": "Reason:",
					"reqd": 1,
				}
			],
			primary_action: function() {
				var data = d.get_values();
				update_now(data.reason, 1)
			}
		});
		d.show();
	} else {
		update_now("", 0)
	}
}

erpnext.asset.scrap_asset = function(frm) {
	var fields = [
		{
			fieldname: 'disposal_date',
			fieldtype: 'Date',
			label: __('Disposal Date'),
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: 'warning_html',
			fieldtype: 'HTML',
			options: ''
		},
		{
			fieldname: 'submit_jv',
			fieldtype: 'Check',
			label: __('Submit Journal Entry'),
			default: 1,
			description: __('If unchecked, the disposal Journal Entry will be saved as Draft')
		}
	];

	var d = new frappe.ui.Dialog({
		title: __('Scrap Asset'),
		fields: fields,
		primary_action_label: __('Scrap'),
		primary_action: function() {
			var values = d.get_values();
			if (!values) return;
			d.hide();
			frappe.call({
				args: {
					"asset_name": frm.doc.name,
					"disposal_date": values.disposal_date,
					"submit_jv": values.submit_jv ? 1 : 0
				},
				method: "erpnext.assets.doctype.asset.depreciation.scrap_asset",
				callback: function(r) {
					cur_frm.reload_doc();
				}
			});
		}
	});

	function check_disposal_date(disposal_date) {
		if (!disposal_date) return;
		frappe.call({
			method: "erpnext.assets.doctype.asset.depreciation.check_unposted_depr_before_disposal",
			args: {
				asset_name: frm.doc.name,
				disposal_date: disposal_date
			},
			callback: function(r) {
				if (!r.message) return;
				var html = '';
				if (r.message.future_posted && r.message.future_posted.length > 0) {
					var rows = r.message.future_posted.map(function(e) {
						return '<li>' + e.journal_entry + ' (' + e.schedule_date + ' — '
							+ format_currency(e.depreciation_amount, erpnext.get_currency(frm.doc.company)) + ')</li>';
					}).join('');
					html += '<div class="alert alert-danger" style="margin-top:10px">'
						+ '<strong>' + __('Cannot proceed!') + '</strong> '
						+ __('There are posted depreciation entries after {0}. Cancel them first:', [disposal_date])
						+ '<ul style="margin:5px 0 0 15px">' + rows + '</ul>'
						+ '</div>';
					d.get_primary_btn().prop('disabled', true);
				} else {
					d.get_primary_btn().prop('disabled', false);
				}
				if (r.message.unposted_count > 0) {
					html += '<div class="alert alert-warning" style="margin-top:10px">'
						+ __('There are {0} unposted depreciation entry/entries on or before {1}. '
							+ 'Only posted entries will be recognized in the disposal journal.', [
							r.message.unposted_count, disposal_date
						])
						+ '</div>';
				}
				d.fields_dict.warning_html.$wrapper.html(html);
			}
		});
	}

	d.fields_dict.disposal_date.$wrapper.find('input').on('change', function() {
		var val = d.get_value('disposal_date');
		check_disposal_date(val);
	});

	d.show();
	check_disposal_date(frappe.datetime.get_today());
};
