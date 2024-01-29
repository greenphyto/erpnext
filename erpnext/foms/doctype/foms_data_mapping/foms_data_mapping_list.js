frappe.listview_settings['FOMS Data Mapping'] = {
	add_fields: ['status'],
	get_indicator: function (doc) {
		if (doc.status === "Mapped") {
			return [__("Mapped"), "green", "status,=,Mapped"];
		} else if (doc.status === "Unknown") {
			return [__("Unknown"), "red", "status,=,Unknown"];
		} 
	},
}