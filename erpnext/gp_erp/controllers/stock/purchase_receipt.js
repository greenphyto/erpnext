frappe.ui.form.on('Purchase Receipt Item', {
	expense_account: function(frm, cdt, cdn) {
		frm.cscript.set_cost_center(frm, cdt, cdn);
	},

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

cur_frm.cscript['set_cost_center'] = function(frm, cdt, cdn) {
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

frappe.ui.form.on("Purchase Taxes and Charges", {
	account_head: function(frm, cdt, cdn) {
		frm.cscript.set_cost_center(frm, cdt, cdn);
	}
});
