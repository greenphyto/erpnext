// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Packing Slip', {
    setup: (frm) => {
        frm.set_query('delivery_note', () => {
            return {
                filters: {
                    docstatus: ["!=", 2],
                }
            }
        });

        frm.set_query('item_code', 'items', (doc, cdt, cdn) => {
            if (!doc.delivery_note) {
                frappe.throw(__('Please select a Delivery Note'));
            } else {
                let d = locals[cdt][cdn];
                return {
                    query: 'erpnext.stock.doctype.packing_slip.packing_slip.item_details',
                    filters: {
                        delivery_note: doc.delivery_note,
                    }
                }
            }
        });
	},

	refresh: (frm) => {
		frm.toggle_display('misc_details', frm.doc.amended_from);
	},

	delivery_note: (frm) => {
		frm.set_value('items', null);

		if (frm.doc.delivery_note) {
			frappe.call({
				method: 'fetch_delivery_note',
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Fetching items from Delivery Note...'),
				callback: function(r) {
                    frm.refresh()
				}
			});
		}
	},

    handling_instruction_template: (frm) => {   
        frm.cscripts.handling_instruction_template(frm);
    }
    
});


frappe.provide("cur_frm.cscripts")
$.extend(cur_frm.cscripts, {
    // terms
    // fetch Terms and Condition from field handling_instruction_template
    handling_instruction_template: function (frm) {
        if (frm.doc.handling_instruction_template) {
            frappe.db.get_value('Terms and Conditions', frm.doc.handling_instruction_template, 'terms', (r) => {
                if (r && r.terms) {
                    frm.set_value('handling_instruction', r.terms);
                }
            });
        }
    }
})