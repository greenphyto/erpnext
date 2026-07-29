frappe.ui.form.on("Purchase Invoice", {
    refresh: function(frm) {
        if (frm.doc.docstatus == 1 && !frm.doc.on_hold) {
            frm.add_custom_button(
                __('Payment Approval'),
                function() {
                    frappe.model.open_mapped_doc({
                        method: "erpnext.gp_erp.controllers.buying.purchase_invoice.make_payment_approval",
                        frm: cur_frm
                    });
                },
                __('Create')
            );
        }
    },

    bank_number: function(frm) {
        frm.events.update_bank_details && frm.events.update_bank_details(frm);
    }
});

frappe.ui.form.on("Purchase Invoice Item", {
    expense_account: function(frm, cdt, cdn) {
        frm.cscript.set_cost_center && frm.cscript.set_cost_center(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        if (frm._in_set_value) return;
        let row = locals[cdt][cdn];
        if (flt(row.rate) === 0 && flt(row.price_list_rate) > 0) {
            frappe.model.set_value(cdt, cdn, "original_rate", row.price_list_rate);
            frm._in_set_value = true;
            frappe.model.set_value(cdt, cdn, "is_free_item", 1);
            frm._in_set_value = false;
        } else if (flt(row.rate) > 0 && cint(row.is_free_item) === 1) {
            frm._in_set_value = true;
            frappe.model.set_value(cdt, cdn, "is_free_item", 0);
            frm._in_set_value = false;
        }
    },
    is_free_item: function(frm, cdt, cdn) {
        if (frm._in_set_value) return;
        let row = locals[cdt][cdn];
        if (cint(row.is_free_item)) {
            frappe.model.set_value(cdt, cdn, "original_rate", row.price_list_rate);
            frm._in_set_value = true;
            frappe.model.set_value(cdt, cdn, "rate", 0);
            frm._in_set_value = false;
        } else {
            frm._in_set_value = true;
            frappe.model.set_value(cdt, cdn, "rate", row.original_rate || row.price_list_rate || 0);
            frm._in_set_value = false;
        }
    }
});

frappe.ui.form.on("Purchase Taxes and Charges", {
    account_head: function(frm, cdt, cdn) {
        frm.cscript.set_cost_center && frm.cscript.set_cost_center(frm, cdt, cdn, "account_head");
    }
});
