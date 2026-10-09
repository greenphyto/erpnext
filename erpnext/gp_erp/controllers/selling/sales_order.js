frappe.ui.form.on("Sales Order", {
    is_pledge: function(frm) {
        if (cint(frm.doc.is_pledge) == 0) return;
        frm.set_value("naming_series", 'PLN.###./.YYYY');
        frm.set_value("po_no", "For Pledge");
        frm.set_value("po_date", "");
        frappe.db.get_value("Company", frm.doc.company, ["donor_customer"]).then(r => {
            frm.set_value("customer", r.message.donor_customer);
        });
    }
});

frappe.ui.form.on("Sales Order Item", {
    uom: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        frappe.db.get_value("Packaging", d.uom, "total_weight").then(r => {
            frappe.model.set_value(cdt, cdn, "weight_in_unit", r.message.total_weight);
        });
    }
});
