frappe.ui.form.on("Delivery Note", {
    setup: function(frm) {
        frm.set_query("uom", "items", function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            if (!row.item_code) frappe.throw(__("Please select Item"));
            return erpnext.queries.uom({
                parent: row.item_code,
                is_packaging: doc.non_package_item ? 0 : 1,
            });
        });
    },

    onload: function(frm) {
        set_default_delivery_warehouse(frm);
        set_outlet_name(frm);
        set_return_naming_series(frm);
    },

    refresh: function(frm) {
        set_return_naming_series(frm);
    },

    company: function(frm) {
        set_default_delivery_warehouse(frm);
    },

    shipping_address_name: function(frm) {
        set_outlet_name(frm);
    },

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

frappe.ui.form.on("Delivery Note", {
    is_donation: (frm) => set_exclusive_logic(frm, "is_donation"),
    is_giveaway: (frm) => set_exclusive_logic(frm, "is_giveaway"),
    is_return: (frm) => set_exclusive_logic(frm, "is_return"),
    is_replacement: (frm) => set_exclusive_logic(frm, "is_replacement"),
    is_marketing: (frm) => set_exclusive_logic(frm, "is_marketing"),
    is_production: (frm) => set_exclusive_logic(frm, "is_production"),
    is_pledge: (frm) => set_exclusive_logic(frm, "is_pledge"),
});

function set_return_naming_series(frm) {
    if (frm.doc.is_return && frm.doc.naming_series !== "DO-RET-.YYYY.-.###") {
        frm.set_value("naming_series", "DO-RET-.YYYY.-.###");
    }
}

function set_default_delivery_warehouse(frm) {
    if (!frm.is_new() || frm.doc.set_warehouse || !frm.doc.company) return;
    frappe.db.get_value("Company", frm.doc.company, "default_warehouse").then(r => {
        const warehouse = r.message && (r.message.default_warehouse || frappe.sys_defaults.default_selling_warehouse);
        if (warehouse && !frm.doc.set_warehouse) frm.set_value("set_warehouse", warehouse);
    });
}

function set_outlet_name(frm) {
    if (!frm.doc.shipping_address_name) {
        frm.set_value("outlet_name", "");
        return;
    }
    frappe.db.get_value("Address", frm.doc.shipping_address_name, "outlet_name").then(r => {
        frm.set_value("outlet_name", r.message ? r.message.outlet_name || "" : "");
    });
}

function set_exclusive_logic(frm, changed_field) {
    if (!cint(frm.doc[changed_field])) return;

    [
        "is_donation",
        "is_giveaway",
        "is_return",
        "is_replacement",
        "is_marketing",
        "is_production",
        "is_pledge",
    ].forEach(field => {
        if (field !== changed_field && cint(frm.doc[field])) {
            frm.set_value(field, 0);
        }
    });
} 

function set_donation_expense(frm, account) {
    if (!account) return;
    (frm.doc.items || []).forEach(row => {
        frappe.model.set_value(row.doctype, row.name, "expense_account", account);
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
