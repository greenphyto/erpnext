frappe.ui.form.on("Warehouse Location", {
	setup(frm) {
		frm.set_query("warehouse", () => ({
			filters: { is_group: 0, disabled: 0 },
		}));
	},
	before_load(frm) {
		if (frm.is_new() && frm.doc.is_mixed_storage_allowed === undefined) {
			frm.set_value("is_mixed_storage_allowed", 1);
		}
		if (frm.is_new() && !frm.doc.warehouse) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Warehouse Location Settings",
					fieldname: "default_warehouse",
				},
				callback(r) {
					if (r && r.message && r.message.default_warehouse) {
						frm.set_value("warehouse", r.message.default_warehouse);
					}
				},
			});
		}
	},
	warehouse(frm) {
		update_location_code_preview(frm);
	},
	aisle_row(frm) {
		update_location_code_preview(frm);
	},
	bay_column(frm) {
		update_location_code_preview(frm);
	},
	level_tier(frm) {
		update_location_code_preview(frm);
	},
});

function update_location_code_preview(frm) {
	if (!frm.doc.warehouse || !frm.doc.aisle_row || !frm.doc.bay_column || !frm.doc.level_tier) {
		frm.set_value("location_code", "");
		return;
	}
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Warehouse",
			filters: { name: frm.doc.warehouse },
			fieldname: "warehouse_code",
		},
		callback(r) {
			if (r && r.message && r.message.warehouse_code) {
				var code = [
					r.message.warehouse_code,
					frm.doc.aisle_row,
					frm.doc.bay_column,
					frm.doc.level_tier,
				].join("-");
				frm.set_value("location_code", code);
			}
		},
	});
}
