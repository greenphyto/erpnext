frappe.ui.form.on("Payment Entry", {
    refresh: function(frm) {
        if (frm.is_dirty()) {
            if (frm.doc.payment_type == "Receive") {
                frm.set_value("naming_series", "RV.###./.YYYY");
            } else if (frm.doc.payment_type == "Pay") {
                frm.set_value("naming_series", "PV.###./.YYYY");
            }
        }
    },

    payment_type: function(frm) {
        if (frm.doc.payment_type == "Receive") {
            frm.set_value("naming_series", "RV.###./.YYYY");
        } else if (frm.doc.payment_type == "Pay") {
            frm.set_value("naming_series", "PV.###./.YYYY");
        }
    }
});

function set_cost_center(frm, account = "", field = "") {
    return new Promise((resolve) => {
        erpnext.utils.get_cost_center(account, frm.doc.company).then(r => {
            frm.set_value(field, r.value);
            resolve();
        });
    });
}
