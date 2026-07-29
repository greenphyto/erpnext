frappe.ui.form.on("Journal Entry", {
    setup: function(frm) {
        frm.add_fetch("bank_account", "account", "account");
    },

    is_debit_note: function(frm) {
        if (frm.doc.is_debit_note) {
            frm.set_df_property('return_against', 'reqd', 1);
            frm.set_df_property('update_stock', 'hidden', 1);
        } else {
            frm.set_df_property('update_stock', 'hidden', 0);
            frm.set_df_property('return_against', 'reqd', 0);
        }
    },

    company: function(frm) {
        erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
    }
});

cur_frm.cscript.update_totals = function(doc) {
    var td = 0.0; var tc = 0.0;
    var accounts = doc.accounts || [];
    for (var i in accounts) {
        td += flt(accounts[i].debit, precision("debit", accounts[i]));
        tc += flt(accounts[i].credit, precision("credit", accounts[i]));
    }
    var gst_entry = doc.gst_entry || [];
    for (var i in gst_entry) {
        td += flt(gst_entry[i].debit, precision("debit", gst_entry[i]));
        tc += flt(gst_entry[i].credit, precision("credit", gst_entry[i]));
    }
    var doc = locals[doc.doctype][doc.name];
    doc.total_debit = td;
    doc.total_credit = tc;
    doc.difference = flt((td - tc), precision("difference"));
    refresh_many(['total_debit', 'total_credit', 'difference']);
};
