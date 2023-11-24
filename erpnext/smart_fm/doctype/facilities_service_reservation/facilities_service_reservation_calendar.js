frappe.views.calendar["Facilities Service Reservation"] = {
	field_map: {
		start: "from_time",
		end: "to_time",
		id: "name",
		allDay: "all_day",
		title: "service",
		status: "status",
	},
	style_map: {
		Issued: "orange",
		Accepted: "blue",
		Started: "green",
		Finished: "purple",
		Cancelled: "grey",
		Rejected: "red",
	},
    options:{
        timeFormat: 'HH:mm'
    },
	get_events_method: "erpnext.smart_fm.doctype.facilities_service_reservation.facilities_service_reservation.get_events",
};
