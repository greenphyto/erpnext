frappe.ui.form.on("Purchase Order", {
    supplier: function(frm) {
        if (!frm.doc.supplier) return;
        frappe.call({
            method: "erpnext.gp_erp.controllers.buying.purchase_order.get_internal_supplier_currency",
            args: { supplier: frm.doc.supplier },
            callback(r) {
                if (!r.message) return;
                const currency = r.message;
                if (!currency) return;
                if (frm.doc.currency !== currency) {
                    frm.set_value("currency", currency);
                    frm.set_value("buying_price_list", "");
                    frappe.show_alert(`Currency set to ${currency} (Internal Supplier)`);
                }
            }
        });
    }
});

frappe.ui.form.on("Purchase Order Item", {
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
