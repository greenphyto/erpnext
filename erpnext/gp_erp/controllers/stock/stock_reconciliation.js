frappe.ui.form.on("Stock Reconciliation", {
	setup: function(frm) {
		frm.set_query("item_code", "items", function(doc, cdt, cdn) {
			return {
				filters: {
					"is_stock_item": 1,
					"item_group": ['in', ['Raw Material', 'Products']],
					"has_batch_no": 1
				}
			};
		});
		frm.set_query("batch_no", "items", (doc, cdt, cdn) => {
			var d = locals[cdt][cdn];
			if (!d.item_code) {
				frappe.throw(__("Please select Item."));
			}
			return {
				filters: {
					item: d.item_code
				},
				query: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_batch_numbers"
			};
		});
	}
});
