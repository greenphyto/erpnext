frappe.ui.form.on("Company", {
	setup: function(frm) {
		frappe.call({
			method: "frappe.core.doctype.system_settings.system_settings.load",
			callback: function(data) {
				frappe.all_timezones = data.message.timezones;
				frm.set_df_property("time_zone", "options", frappe.all_timezones);
			},
		});
	},

	refresh: function(frm) {
		// GP: company-specific queries
	}
});
