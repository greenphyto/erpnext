// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Number', {
	after_save: function (frm) {
		frappe.run_serially([
			() => frappe.timeout(1),
			() => {
				const last_doc = {
					"doctype":frm.doc.party_type,
					"docname":frm.doc.party
				}
				if (
					frappe.dynamic_link &&
					frappe.dynamic_link.doc &&
					frappe.dynamic_link.doc.name == last_doc.docname &&
					frappe.dynamic_link.doc.doctype == last_doc.doctype
				) {
					frappe.flags.hard_reload = 1;
					frappe.set_route("Form", last_doc.doctype, last_doc.docname);
				}
			},
		]);
	}
});