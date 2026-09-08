// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Buying Settings', {
	update_supplier: function(frm) {
		let series_options = (frm.doc.default_supplier_account || []).map(d => d.code.replace("...", ""));
		series_options = [...new Set(series_options)];

		let d = new frappe.ui.Dialog({
			title: __("Update Supplier Account"),
			fields: [
				{
					fieldname: "update_all_series",
					fieldtype: "Check",
					label: __("Update All Series"),
					default: 0
				},
				{
					fieldname: "series",
					fieldtype: "MultiSelect",
					label: __("Select Series Code"),
					options: series_options,
					reqd: 1,
					depends_on: "eval:!doc.update_all_series"
				},
				{
					fieldname: "mode",
					fieldtype: "Select",
					label: __("Update Mode"),
					options: "Only if not set\nReplace all",
					default: "Only if not set",
					reqd: 1
				}
			],
			primary_action_label: __("Update"),
			primary_action: function(values) {
				d.hide();
				let series_list = values.update_all_series
					? series_options
					: values.series.split(",").map(s => s.trim());
				frappe.call({
					method: "update_supplier_account",
					doc: frm.doc,
					args: {
						series_filter: series_list,
						mode: values.mode
					},
					callback: function() {
						frappe.show_alert(__("Success"));
					}
				});
			}
		});
		d.show();
	},
	setup: function(frm){
		frm.set_query("requester", "purchase_approval", function (doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.filter_purchase_user" }
		});
		frm.set_query("approver", "purchase_approval", function (doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.filter_purchase_manager" }
		});
	}
});

frappe.tour['Buying Settings'] = [
	{
		fieldname: "supp_master_name",
		title: "Supplier Naming By",
		description: __("By default, the Supplier Name is set as per the Supplier Name entered. If you want Suppliers to be named by a <a href='https://docs.erpnext.com/docs/user/manual/en/setting-up/settings/naming-series' target='_blank'>Naming Series</a> choose the 'Naming Series' option."),
	},
	{
		fieldname: "buying_price_list",
		title: "Default Buying Price List",
		description: __("Configure the default Price List when creating a new Purchase transaction. Item prices will be fetched from this Price List.")
	},
	{
		fieldname: "po_required",
		title: "Purchase Order Required for Purchase Invoice & Receipt Creation",
		description: __("If this option is configured 'Yes', ERPNext will prevent you from creating a Purchase Invoice or Receipt without creating a Purchase Order first. This configuration can be overridden for a particular supplier by enabling the 'Allow Purchase Invoice Creation Without Purchase Order' checkbox in the Supplier master.")
	},
	{
		fieldname: "pr_required",
		title: "Purchase Receipt Required for Purchase Invoice Creation",
		description: __("If this option is configured 'Yes', ERPNext will prevent you from creating a Purchase Invoice without creating a Purchase Receipt first. This configuration can be overridden for a particular supplier by enabling the 'Allow Purchase Invoice Creation Without Purchase Receipt' checkbox in the Supplier master.")
	}
];
