frappe.ui.form.on("Batch Location", {
	before_load(frm) {
		frm.set_df_property("batch", "read_only", 1);
		frm.set_df_property("item", "read_only", 1);
		frm.set_df_property("warehouse_location", "read_only", 1);
		frm.set_df_property("warehouse", "read_only", 1);
		frm.set_df_property("qty", "read_only", 1);
		frm.set_df_property("stock_uom", "read_only", 1);
		frm.set_df_property("uom", "read_only", 1);
		frm.set_df_property("conversion_factor", "read_only", 1);
		frm.set_df_property("last_updated", "read_only", 1);
	},
});
