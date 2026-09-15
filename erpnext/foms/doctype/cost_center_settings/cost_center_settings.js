// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cost Center Settings', {
	refresh: function (frm) {
		// Load from Accounts button
		frm.add_custom_button(__('Load from Accounts'), () => {
			if (!frm.doc.company) {
				frappe.throw(__('Company must be set!'));
			}

			// Show confirmation dialog
			frappe.confirm(
				__('These lists will be removed, continue to load from account?'),
				() => {
					// User clicked Yes
					frappe.call({
						method: 'load_from_accounts',
						doc: frm.doc,
						callback: function (r) {
							// Rebuild the doc from server response
							// if (r && r.message) {
							// 	frm.doc.cost_center = r.message;
							// }
							frm.refresh_field('cost_center');
							frm.dirty();
							frappe.msgprint(__('Account and cost center mapping loaded successfully.'));
						},
					});
				},
				() => {
					// User clicked No - do nothing
				}
			);
		});

		// Set query filters for child table
		frm.set_query('account', 'cost_center', (doc) => {
			return {
				filters: {
					company: doc.company,
				},
			};
		});

		frm.set_query('cost_center', 'cost_center', (doc) => {
			return {
				filters: {
					company: doc.company,
				},
			};
		});
	},
});
