frappe.listview_settings['Email Invoice'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status == "Unknown") {
			return [__("Unknown"), "orange", "status,=,Unknown"];
        } else if(doc.status == "Pending") {
			return [__("Pending"), "gray", "status,=,Pending"];
        } else if(doc.status == "Matched") {
			return [__("Matched"), "green", "status,=,Matched"];
		}
	}
};
