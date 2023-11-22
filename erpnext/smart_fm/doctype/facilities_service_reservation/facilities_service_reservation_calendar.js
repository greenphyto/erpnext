frappe.views.calendar["Facilities Service Reservation"] = {
	field_map: {
		start: "from_time",
		end: "to_time",
		id: "name",
		allDay: "all_day",
		title: "service",
		status: "status",
		// color: "color",
	},
	style_map: {
		Issued: "blue",
		Accepted: "orange",
	},
    options:{
        timeFormat: 'HH:mm'
    },
	get_events_method: "erpnext.smart_fm.doctype.facilities_service_reservation.facilities_service_reservation.get_events",
};
