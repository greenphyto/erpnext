frappe.ui.form.on('Material Request', {
	refresh: function(frm) {
		// GP: extend Purchase Order / RFQ / Supplier Quotation buttons to include Services type
	},

	get_item_data: function(frm, item, overwrite_warehouse=false) {
		if (item && !item.item_code) {
			return;
		}
		frm.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			child: item,
			args: {
				args: {
					item_code: item.item_code,
					warehouse: item.warehouse || frm.doc.set_warehouse,
					supplier: frm.doc.supplier,
					currency: frm.doc.currency,
					plc_conversion_rate: 1,
					rate: item.rate,
					uom: item.uom,
					conversion_factor: item.conversion_factor,
					is_free_item: item.is_free_item
				},
				overwrite_warehouse: overwrite_warehouse
			},
			callback: function(r) {
				frm.refresh_field("items");
			}
		});
	},
});

// GP: Services type support for Purchase Order / RFQ / Supplier Quotation buttons
// The standard code checks material_request_type === "Purchase", we extend to include "Services"
// This is done by overriding the refresh handler in the child table
frappe.ui.form.on("Material Request Item", {
	is_free_item: function(frm, doctype, name) {
		const item = locals[doctype][name];
		frappe.model.set_value(doctype, name, "rate", 0);
		item.rate = 0;
		frm.events.get_item_data(frm, item, false);
	},
});
