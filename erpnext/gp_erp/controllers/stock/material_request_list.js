frappe.listview_settings['Material Request'] = {
	add_fields: ["purchase_order", "material_request_type", "status", "per_ordered", "per_received", "transfer_status"],
	get_indicator: function(doc) {
		var precision = frappe.defaults.get_default("float_precision");
		if (doc.status=="Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
		} else if (doc.material_request_type == "Purchase" && flt(doc.per_ordered, precision) == 100) {
			return [__("Ordered"), "green", "per_ordered,=,100"];
		} else if (doc.material_request_type == "Material Transfer" && flt(doc.per_received, precision) == 100) {
			return [__("Material Transferred"), "green", "per_received,=,100"];
		} else if (doc.material_request_type == "Material Issue" && flt(doc.per_issued, precision) == 100) {
			return [__("Material Issued"), "green", "per_issued,=,100"];
		} else if (doc.material_request_type == "Manufacture" && flt(doc.per_produced, precision) == 100) {
			return [__("Manufactured"), "green", "per_produced,=,100"];
		} else if (doc.material_request_type == "Subcontracting" && flt(doc.per_ordered, precision) == 100) {
			return [__("Ordered"), "green", "per_ordered,=,100"];
		}
		return ["", ""];
	},
	onload: function(listview) {
		// GP: no additional onload
	}
};
