frappe.ui.form.on("Sales Invoice", {
    is_return: function(frm) {
        frm.set_value("naming_series", "CN.###./.YYYY");
    },

    is_pledge: function(frm) {
        if (cint(frm.doc.is_pledge) == 0) {
            frm.set_value("customer", "");
            frm.set_value("naming_series", "INV.###./.YYYY");
            frm.set_value("po_no", "");
            return;
        }
        frm.set_value("naming_series", "DON.###./.YYYY");
        frm.set_value("po_no", "For Pledge");
        frm.set_value("po_date", "");
        frappe.db.get_value("Company", frm.doc.company, "donor_customer").then(r => {
            if (r.message && r.message.donor_customer) {
                frm.set_value("customer", r.message.donor_customer);
            }
        });
    },

    debit_note_transaction: function(frm) {
        if (frm.doc.debit_note_transaction) {
            if (frm.doc.customer) {
                frappe.db.get_value("Customer", frm.doc.customer, ["debit_note_enable", "name"]).then(r => {
                    if (!r.message.debit_note_enable) {
                        frm.set_value("customer", "");
                        frappe.throw(__(`Customer <b>${r.message.name}</b> is not enable for debit note transaction`));
                    }
                });
            }
            frm.set_value("items", []);
        }
    },

    onload: function(frm) {
        frm.redemption_conversion_factor = null;
    }
});

cur_frm.cscript["set_cost_center"] = function(frm, cdt, cdn, field_account = "expense_account") {
    var d = locals[cdt][cdn];
    return new Promise((resolve) => {
        if (d[field_account]) {
            erpnext.utils.get_cost_center(d[field_account], frm.doc.company).then(r => {
                frappe.model.set_value(cdt, cdn, "cost_center", r.value);
                frappe.model.set_value(cdt, cdn, "lock_cost_center", r.lock);
            });
        } else {
            frappe.model.set_value(cdt, cdn, "cost_center", "");
            frappe.model.set_value(cdt, cdn, "lock_cost_center", 0);
            resolve();
        }
    });
};

frappe.ui.form.on("Sales Invoice Item", {
    income_account: function(frm, cdt, cdn) {
        frm.cscript.set_cost_center(frm, cdt, cdn, "income_account");
    },
    expense_account: function(frm, cdt, cdn) {
        frm.cscript.set_cost_center(frm, cdt, cdn);
    }
});

frappe.ui.form.on("Sales Taxes and Charges", {
    account_head: function(frm, cdt, cdn) {
        frm.cscript.set_cost_center(frm, cdt, cdn, "account_head");
    }
});
