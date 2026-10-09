frappe.ui.form.on("Item", {
	setup: function(frm) {
		frm.set_query("asset_code", () => {
			return {
				query: "erpnext.assets.doctype.asset.asset.filter_account_for_asset_code",
			};
		});
	},

	refresh: function(frm) {
		if (frm.doc.material_group) {
			frm.set_df_property("material_group", "read_only", 1);
		}
		frappe.already_confirmed = false;
		frm._initial_doc = frappe.utils.deep_clone(frm.doc);
	},

	validate: function(frm) {
		erpnext.item.weight_to_validate(frm);
		erpnext.item.allow_uom_global_change(frm);
	},

	asset_code: function(frm) {
		if (frm.doc.asset_code) {
			frappe.call({
				method: "erpnext.assets.doctype.asset.asset.get_default_asset_code_data",
				args: {
					asset_code: frm.doc.asset_code
				},
				callback: function(r) {
					frm.set_value("asset_category", r.message.asset_category);
					frm.set_value("asset_naming_series", r.message.series);
					var company = r.message.company || frappe.defaults.get_default('company');
					var row = $.grep(frm.doc.item_defaults, function(r) {
						if (r.company == "Greenphyto Pte Ltd") return r;
					});
					if (row && row.length) {
						row = row[0];
						frappe.model.set_value(row.doctype, row.name, "expense_account", r.message.account);
					} else {
						row = frm.add_child("item_defaults");
						row.company = company;
						row.expense_account = r.message.account;
					}
					frm.refresh_field("item_defaults");
				}
			});
		} else {
			frm.set_value("asset_category", "");
		}
	},
});

frappe.ui.form.on('Item Reorder', {
	pic: function(frm, cdt, cdn) {
		frappe.call({
			method: "erpnext.stock.doctype.item.item.get_default_pic",
			args: {
				"code": frm.doc.name
			},
			callback: function(r) {
				frappe.model.set_value(cdt, cdn, "pic", r.message.pic);
			}
		});
	}
});

frappe.ui.form.on("UOM Conversion Detail", {
	cf_view: function(frm, cdt, cdn) {
		erpnext.item.control_uom_conversion(frm, cdt, cdn);
	}
});

$.extend(erpnext.item, {
	add_foms_sync_button: function(frm) {
		if (frm.doc.__islocal) return;
		frm.add_custom_button(__("Sync to FOMS"), function() {
			frappe.confirm(
				__("Sync this item to FOMS?"),
				function() {
					frappe.call({
						method: "erpnext.controllers.foms.create_new_foms_item",
						args: { item_code: frm.doc.name },
						freeze: true,
						freeze_message: __("Syncing item to FOMS..."),
						callback: function(r) {
							if (!r || r.exc) return;
							const result = r.message || __("Completed");
							const is_blocked = ["Not Allowed Group"].includes(result);
							frappe.show_alert({
								message: __("FOMS sync result: {0}", [result]),
								indicator: is_blocked ? "orange" : "green"
							});
							if (!is_blocked) frm.reload_doc();
						}
					});
				}
			);
		}, __("Actions"));
	},

	allow_uom_global_change: function(frm) {
		function revert_uom() {
			$.each(frm.doc.uoms, function(i, row) {
				frappe.model.set_value(row.doctype, row.name, "global_description", row.origin_description);
			});
		}

		var uom_changes = {};
		frm.doc.uoms.forEach(function(row) {
			if (row.origin_description != row.global_description && row.global_description && row.origin_description) {
				uom_changes[row.uom] = row.global_description;
			}
		});

		if (uom_changes && Object.keys(uom_changes).length > 0 && !frappe.already_confirmed) {
			let uom_list = "<ul>";
			for (let [key, val] of Object.entries(uom_changes)) {
				uom_list += `<li>${key} → <b>${val}</b></li>`;
			}
			uom_list += "</ul>";
			frappe.throw({
				title: __("Confirm UOM Change"),
				message: __("The global description of UOMs have been modified:<br>{0}Do you confirm applying these changes globally?", [uom_list]),
				primary_action: {
					label: __("Yes, and Save"),
					action() {
						frappe.validated = true;
						frappe.already_confirmed = true;
						cur_dialog.hide();
						frm.save();
					}
				},
				secondary_action: {
					label: __("Cancel"),
					action() {
						frappe.validated = false;
						frappe.already_confirmed = true;
						cur_dialog.hide();
						revert_uom();
						frm.save();
					}
				}
			});
			frappe.validated = false;
		}
	},

	control_uom_conversion: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.idx == 1) {
			frappe.model.set_value(cdt, cdn, "description", "Stock UOM Value");
		} else {
			frappe.model.set_value(cdt, cdn, "conversion_factor", row.cf_view);
			frappe.model.set_value(cdt, cdn, "description", `1 ${row.uom} equal to ${row.cf_view} ${frm.doc.stock_uom}`);
		}
	}
});
