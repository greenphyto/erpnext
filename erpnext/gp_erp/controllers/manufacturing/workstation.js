frappe.ui.form.on("Workstation", {
	setup: function(frm) {
		frm.set_query("item_code", () => {
			return {
				filters: {
					"item_group": "Products",
					"disabled": 0
				}
			}
		});
	},

	refresh: function(frm) {
		frm.cscript.change_label();
		if (!frm.is_new() && frm.doc.docstatus == 0) {
			frm.add_custom_button(__("New Version"), function() {
				let new_ws = frappe.model.copy_doc(frm.doc);
				frappe.set_route("Form", "Workstation", new_ws.name);
			});
		}
	},

	calculation_type: function(frm) {
		frm.cscript.change_label();
	}
});

$.extend(cur_frm.cscript, {
	change_label: function() {
		var frm = this.frm;
		var fields = ['per_qty_rate_electricity', 'per_qty_rate_wages', 'per_qty_rate_machinery', 'per_qty_rate', 'per_qty_rate_consumable'];
		var desc = "per qty";
		var label = "Net Hour Rate";
		if (frm.doc.calculation_type == "Per KG") {
			desc = "per KG";
			label = "Net Cost Rate";
		}
		frm.set_df_property("per_qty_rate", 'label', label);
		fields.forEach(field => {
			frm.set_df_property(field, 'description', desc);
		});
	}
});
