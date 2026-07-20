frappe.ui.form.on("Warehouse Action", {
	setup(frm) {
		frm.set_query("from_location", () => ({
			filters: {
				warehouse: frm.doc.warehouse,
				disabled: 0,
				status: ["!=", "Blocked"],
			},
		}));
		frm.set_query("to_location", () => ({
			filters: {
				warehouse: frm.doc.warehouse,
				disabled: 0,
				status: ["!=", "Blocked"],
			},
		}));
	},
	batch(frm) {
		if (!frm.doc.batch) return;
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Batch",
				filters: { name: frm.doc.batch },
				fieldname: "item",
			},
			callback(r) {
				if (r && r.message) {
					frm.set_value("item", r.message.item);
					frappe.call({
						method: "frappe.client.get_value",
						args: {
							doctype: "Item",
							filters: { name: r.message.item },
							fieldname: "stock_uom",
						},
						callback(r2) {
							if (r2 && r2.message) {
								frm.set_value("stock_uom", r2.message.stock_uom);
							}
						},
					});
				}
			},
		});
	},
	qty(frm) {
		update_stock_qty_preview(frm);
	},
	conversion_factor(frm) {
		update_stock_qty_preview(frm);
	},
});

function update_stock_qty_preview(frm) {
	frm.set_value(
		"stock_qty",
		flt(frm.doc.qty || 0) * flt(frm.doc.conversion_factor || 0)
	);
}
