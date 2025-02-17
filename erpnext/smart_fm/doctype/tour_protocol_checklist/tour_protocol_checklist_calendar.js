frappe.views.calendar["Tour Protocol Checklist"] = {
	field_map: {
		start: "from_time",
		end: "to_time",
		id: "name",
		title: "group_name",
		status: "status",
	},
    options:{
        timeFormat: 'HH:mm',
		slotEventOverlap: false,
		slotDuration: '00:15:00',
		slotMinTime: "06:00:00",
		slotMaxTime: "18:30:00",
		axisFormat: 'HH:mm',
    },
	get_events_method: "erpnext.smart_fm.doctype.tour_protocol_checklist.tour_protocol_checklist.get_events",
	hide_sidebar: true,
	before_render: (calendar)=>{
		// calendar.custom = new TourCards(calendar);
	}
};






