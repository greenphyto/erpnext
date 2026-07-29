frappe.ui.form.on("Stock Entry", {
    setup: function(frm) {
        frm.set_query("asset_code", "items", () => {
            return { query: "erpnext.assets.doctype.asset.asset.filter_account_for_asset_code" };
        });
        frm.set_query("stock_entry_type", () => {
            return { filters: { disabled: 0 } };
        });
    },

    refresh: function(frm) {
        if (frm.doc.stock_entry_type_view == "Conversion from Inventory to Fixed Asset" && frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Create Asset'), function() {
                frappe.call({
                    method: "erpnext.gp_erp.controllers.stock.stock_entry.create_asset_from_stock_entry",
                    args: { se_name: frm.doc.name },
                    callback: (r) => {}
                });
            }).removeClass("btn-default").addClass("btn-warning");
        }
    },

    validate_purpose: function(frm) {
        if (frm.doc.stock_entry_type_view) {
            frappe.call({
                method: "frappe.client.get_value",
                args: { doctype: "Stock Entry Type", filters: { name: frm.doc.stock_entry_type_view }, fieldname: "purpose" },
                callback: function(r) {
                    if (r.message) frm.set_value("purpose", r.message.purpose);
                }
            });
        }
    }
});

cur_frm.cscript["set_cost_center"] = function(frm, cdt, cdn) {
    var d = locals[cdt][cdn];
    return new Promise((resolve) => {
        if (d.expense_account) {
            erpnext.utils.get_cost_center(d.expense_account, frm.doc.company).then(r => {
                frappe.model.set_value(cdt, cdn, "cost_center", r.value);
            });
        } else {
            frappe.model.set_value(cdt, cdn, "cost_center", "");
            resolve();
        }
    });
};

frappe.ui.form.on("Stock Entry Detail", {
    expense_account: function(frm, cdt, cdn) {
        frm.cscript.set_cost_center(frm, cdt, cdn).then(() => {
            erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "expense_account");
        });
    },
    asset_code: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        if (d.asset_code) {
            frappe.db.get_value("Asset Code Map", { parent: "Accounts Settings", account: d.asset_code }, "default_asset_category", r => {
                if (!r.default_asset_category) {
                    frappe.msgprint(`Missing default Asset Category for <b>${d.asset_code}</b>.`);
                    frappe.model.set_value(cdt, cdn, "asset_category", "");
                } else {
                    frappe.model.set_value(cdt, cdn, "asset_category", r.default_asset_category);
                }
            }, "Accounts Settings");
        } else {
            frappe.model.set_value(cdt, cdn, "asset_category", "");
        }
        frappe.model.set_value(cdt, cdn, "expense_account", d.asset_code);
    }
});
