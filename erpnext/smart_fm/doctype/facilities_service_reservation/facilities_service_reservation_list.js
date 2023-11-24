frappe.listview_settings['Facilities Service Reservation'] = {
	add_fields: ["service", "status", "email_address"],
	get_indicator: function(doc) {
		var status_list = {
			Issued: [__("Issued"), "orange", "status,=,Issued"],
			Accepted: [__("Accepted"), "blue", "status,=,Accepted"],
			Started: [__("Started"), "green", "status,=,Started"],
			Finished: [__("Finished"), "purple", "status,=,Finished"],
			Cancelled: [__("Cancelled"), "grey", "status,=,Cancelled"],
			Rejected: [__("Rejected"), "red", "status,=,Rejected"],
		}

		return status_list[doc.status]
	},
}