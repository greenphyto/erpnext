// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Reimbursement Claim', {
  onload: function (frm) {
    if (frm.is_new()) {
      frappe.db.get_value("User", frappe.session.user, ["full_name"])
      .then(r => {
        let values = r.message;
        frm.set_value("claim_by", values.full_name);
      });
    }
  },
});
