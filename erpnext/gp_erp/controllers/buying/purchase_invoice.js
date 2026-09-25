frappe.ui.form.on("Purchase Invoice", {
    gst_input_tax: function(frm) {
        if (frm.doc.gst_input_tax) {
            frm.set_value("non_stock_item", 1);
            frm.clear_table("items");
            const row = frm.add_child("items");
            frappe.model.set_value(row.doctype, row.name, "item_code", "Non-stock");
            frappe.model.set_value(row.doctype, row.name, "item_name_view", "GST Input");
            frappe.model.set_value(row.doctype, row.name, "qty", 1);
            frm.set_df_property("non_stock_item", "hidden", 1);
        } else {
            frm.set_df_property("non_stock_item", "hidden", 0);
        }
        frm.refresh_field("items");
    },

    base_value_for_gst_input: function(frm) {
        frm.set_value(
            "base_currency_of_base_value",
            flt(frm.doc.conversion_rate) * flt(frm.doc.base_value_for_gst_input)
        );
    },

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

cur_frm.cscript.set_cost_center = function(frm, cdt, cdn, field_account = "expense_account") {
    const row = locals[cdt][cdn];
    if (!row[field_account]) {
        frappe.model.set_value(cdt, cdn, "cost_center", "");
        frappe.model.set_value(cdt, cdn, "lock_cost_center", 0);
        return;
    }
    return erpnext.utils.get_cost_center(row[field_account], frm.doc.company).then((r) => {
        frappe.model.set_value(cdt, cdn, "cost_center", r.value);
        frappe.model.set_value(cdt, cdn, "lock_cost_center", r.lock);
    });
};

frappe.ui.form.on("Purchase Invoice Item", {
    expense_account: function(frm, cdt, cdn) {
        frm.cscript.set_cost_center && frm.cscript.set_cost_center(frm, cdt, cdn);
    },
    item_name_view: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_name_view) frappe.model.set_value(cdt, cdn, "item_name", row.item_name_view);
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
