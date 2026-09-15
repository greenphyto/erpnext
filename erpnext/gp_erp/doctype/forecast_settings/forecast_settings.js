// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Forecast Settings', {
	refresh: function(frm) {
		console.log(9000)
		frm.set_query("ref_name", 'customers', function() {
			return {
				filters: {
					'disabled': 0,
					'company': frappe.sys_defaults.company
				}
			};
		});
		frm.set_query('ref_name', 'items', function() {
			return {
				filters: {
					'disabled': 0,
					'item_group':"Products"
				}
			};
		});
		frm.set_query('department_default', function() {
			return {
				filters: {
					'company': frm.doc.company_default
				}
			};
		});
	}
});

frappe.ui.form.on('Subtitution Name', {
	customers_add: function(frm,cdt,cdn) {
		var d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'ref_doctype', "Customer");
	}
});
