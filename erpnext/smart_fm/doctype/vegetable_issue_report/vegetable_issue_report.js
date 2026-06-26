// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vegetable Issue Report', {
	refresh: function(frm) {
		// Set status indicator color based on current status
		if (frm.doc.status) {
			const status_colors = {
				'Draft': 'orange',
				'Submitted': 'blue',
				'Acknowledged': 'yellow',
				'Resolved': 'green',
				'Closed': 'darkgrey'
			};
			frm.page.set_indicator(
				frappe._(frm.doc.status),
				status_colors[frm.doc.status] || 'grey'
			);
		}

		// Show workflow actions buttons based on status
		if (frm.doc.docstatus === 0) {
			// Draft - allow Submit
			frm.add_custom_button(__('Submit'), function() {
				frappe.call({
					method: 'frappe.client.set_value',
					args: {
						doctype: 'Vegetable Issue Report',
						name: frm.doc.name,
						fieldname: 'status',
						value: 'Submitted'
					},
					callback: function() {
						frm.reload_doc();
					}
				});
			}, __('Actions'));
		}

		if (frm.doc.status === 'Submitted') {
			frm.add_custom_button(__('Acknowledge'), function() {
				frappe.call({
					method: 'frappe.client.set_value',
					args: {
						doctype: 'Vegetable Issue Report',
						name: frm.doc.name,
						fieldname: 'status',
						value: 'Acknowledged'
					},
					callback: function() {
						frm.reload_doc();
					}
				});
			}, __('Actions'));
		}

		if (frm.doc.status === 'Acknowledged') {
			frm.add_custom_button(__('Mark Resolved'), function() {
				if (!frm.doc.investigation_outcome) {
					frappe.msgprint(__('Please fill in the Investigation Outcome before resolving.'));
					return;
				}
				frappe.call({
					method: 'frappe.client.set_value',
					args: {
						doctype: 'Vegetable Issue Report',
						name: frm.doc.name,
						fieldname: 'status',
						value: 'Resolved'
					},
					callback: function() {
						frm.reload_doc();
					}
				});
			}, __('Actions'));
		}

		if (frm.doc.status === 'Resolved') {
			frm.add_custom_button(__('Close'), function() {
				frappe.call({
					method: 'frappe.client.set_value',
					args: {
						doctype: 'Vegetable Issue Report',
						name: frm.doc.name,
						fieldname: 'status',
						value: 'Closed'
					},
					callback: function() {
						frm.reload_doc();
					}
				});
			}, __('Actions'));
		}
	},

	nutrient_sample_taken: function(frm) {
		// Clear nutrient_sample_date if sample not taken
		if (frm.doc.nutrient_sample_taken !== 'Yes') {
			frm.set_value('nutrient_sample_date', '');
		}
	}
});

// Child table events for Affected Tray Details
frappe.ui.form.on('Vegetable Issue Affected Tray', {
	cage_id: function(frm, cdt, cdn) {
		// Auto-populate location_sz or other logic if needed
	}
});
