frappe.listview_settings['Asset Repair'] = {
	add_fields: ["repair_status", "docstatus"],
	get_indicator: function(doc) {
		if(doc.repair_status=="Completed" && doc.docstatus==1) {
			return [__("Completed"), "green"];
		} else if(doc.repair_status=="Cancelled") {
			return [__("Cancelled"), "red"];
		} else {
			return [__("Pending"), "orange"];
		}
	}
};
