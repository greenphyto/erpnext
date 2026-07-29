frappe.ui.form.on("Delivery Note", {
    is_donation: function(frm) {
        if (cint(frm.doc.is_donation) == 0) return;
        frm.set_value("naming_series", 'DON-.YYYY.-.###');
        frappe.db.get_value("Company", frm.doc.company, ["donation_customer", "donation_account", "donation_warehouse"]).then(r => {
            frm.set_value("customer", r.message.donation_customer);
            frm.set_value("set_warehouse", r.message.donation_warehouse);
            set_donation_expense(frm, r.message.donation_account);
        });
    },
    is_giveaway: function(frm) {
        if (cint(frm.doc.is_giveaway) == 0) return;
        frm.set_value("naming_series", 'GPO-.YYYY.-.###');
        frappe.db.get_value("Company", frm.doc.company, ["internal_staff_customer", "giveaway_account"]).then(r => {
            frm.set_value("customer", r.message.internal_staff_customer);
            set_donation_expense(frm, r.message.giveaway_account);
        });
    },
    is_replacement: function(frm) {
        if (cint(frm.doc.is_replacement) == 0) return;
        frm.set_value("naming_series", 'DO-RPL-.YYYY.-.#####');
        frappe.db.get_value("Company", frm.doc.company, ["sales_replacement_account"]).then(r => {
            set_donation_expense(frm, r.message.sales_replacement_account);
        });
    },
    is_marketing: function(frm) {
        if (cint(frm.doc.is_marketing) == 0) return;
        frm.set_value("naming_series", 'GPM-.YYYY.-.#####');
        frappe.db.get_value("Company", frm.doc.company, ["marketing_customer", "marketing_delivery_account"]).then(r => {
            frm.set_value("customer", r.message.marketing_customer);
            set_donation_expense(frm, r.message.marketing_delivery_account);
        });
    },
    is_production: function(frm) {
        if (cint(frm.doc.is_production) == 0) return;
        frm.set_value("naming_series", 'GPP-.YYYY.-.#####');
        frappe.db.get_value("Company", frm.doc.company, ["production_customer", "production_delivery_account"]).then(r => {
            frm.set_value("customer", r.message.production_customer);
            set_donation_expense(frm, r.message.production_delivery_account);
        });
    },
    is_pledge: function(frm) {
        if (cint(frm.doc.is_pledge) == 0) return;
        frm.set_value("naming_series", 'PON-.YYYY.-.#####');
        frappe.db.get_value("Company", frm.doc.company, ["donor_customer", "donor_delivery_account"]).then(r => {
            frm.set_value("customer", r.message.donor_customer);
            set_donation_expense(frm, r.message.donor_delivery_account);
        });
    },
    is_return: function(frm) {
        frm.set_value("naming_series", "DO-RET-.YYYY.-.###");
    }
});

function set_donation_expense(frm, account) {
    $.each(frm.doc.items, (i, r) => {
        frappe.model.set_value(r.doctype, r.name, "expense_account", account);
    });
    frm.refresh_field("items");
}

cur_frm.cscript["set_cost_center"] = function(frm, cdt, cdn, field_account = "expense_account") {
    if (frm.doc.doctype !== "Delivery Note") return Promise.resolve();
    var d = locals[cdt][cdn];
    return new Promise((resolve) => {
        if (d[field_account]) {
            erpnext.utils.get_cost_center(d[field_account], frm.doc.company).then(r => {
                frappe.model.set_value(cdt, cdn, "cost_center", r.value);
            });
        } else {
            frappe.model.set_value(cdt, cdn, "cost_center", "");
            resolve();
        }
    });
};

frappe.ui.form.on("Delivery Note Item", {
    expense_account: function(frm, cdt, cdn) {
        if (frm.doc.doctype !== "Delivery Note") return;
        frm.cscript.set_cost_center(frm, cdt, cdn);
    }
});

frappe.ui.form.on("Sales Taxes and Charges", {
    account_head: function(frm, cdt, cdn) {
        if (frm.doc.doctype !== "Delivery Note") return;
        frm.cscript.set_cost_center(frm, cdt, cdn, "account_head");
    }
});
