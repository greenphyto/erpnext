frappe.ui.form.on('Mode of Payment', {
	accounts: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.company) {
			frm.set_query("default_account", "accounts", function(doc, cdt, cdn) {
				return {
					filters: {
						'account_type': ['in', 'Bank, Cash, Receivable, Payable'],
						['Account', 'is_group', '=', 0],
						['Account', 'company', '=', d.company]
					}
				};
			});
		}
	}
});
