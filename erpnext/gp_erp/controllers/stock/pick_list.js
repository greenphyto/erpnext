frappe.ui.form.on('Pick List Item', {
	batch_no: (frm, cdt, cdn) => {
		var d = locals[cdt][cdn];
		get_balance_qty(d.batch_no, d.warehouse, d.item_code).then(res => {
			frappe.model.set_value(cdt, cdn, "balance_qty", res);
		});
	}
});

function get_balance_qty(batch_no, warehouse, item_code) {
	return frappe.xcall('erpnext.stock.doctype.batch.batch.get_batch_qty', {
		batch_no, warehouse, item_code
	});
}
