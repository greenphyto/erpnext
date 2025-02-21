frappe.views.calendar["Tour Protocol Checklist"] = {
	field_map: {
		start: "start_time",
		end: "end_time",
		id: "name",
		title: "group_name",
		status: "status",
		allDay: "all_day"
	},
    options:{
        timeFormat: 'HH:mm',
		slotEventOverlap: false,
		slotDuration: '00:15:00',
		slotMinTime: "06:00:00",
		slotMaxTime: "18:30:00",
		axisFormat: 'HH:mm',
		eventRender: (info, el)=>{
			console.log(info, el)
        	var el = $(el);
        	var prop = info
        	var vip = "";
			if (prop.vip_status=="Yes"){
				vip =`<span class="vip-title">VIP</span>`
			}
			el.find(".fc-title").html(`<div>${ prop.title } ${vip}<div>`);
			el.find(".fc-content").append(`<div>${prop.participants || 1} Person<div>`)
			el.find(".fc-content").append(`<div>IC: ${prop.full_name || prop.tour_ic || "-"}<div>`)
		}
    },
	get_events_method: "erpnext.smart_fm.doctype.tour_protocol_checklist.tour_protocol_checklist.get_events",
	hide_sidebar: true,
	before_render: (calendar)=>{
		// calendar.custom = new TourCards(calendar);
	},
};






