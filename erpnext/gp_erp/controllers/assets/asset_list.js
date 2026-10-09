frappe.listview_settings['Asset'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if (doc.status === "Disabled") {
			return [__("Disabled"), "gray", "status,=,Disabled"];
		}
	},
};
