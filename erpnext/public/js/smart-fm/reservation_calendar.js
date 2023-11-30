class FacilityCalendar{
  constructor(class_name){
    this.wrapper = $(class_name);
    this.initial_date = new Date();
    this.run();
  }

  run(){
    var me = this;
    this.load_library().then(()=>{
      me.make_calendar();
    })
  }

  make_calendar(){
    var me = this;
    this.calendar = new FullCalendar.Calendar(this.wrapper[0], {
      initialView: 'timeGridWeek',
      initialDate: this.initial_date,
      slotEventOverlap: false,
      slotDuration: '00:15:00',
      slotMinTime: "06:00:00",
      slotMaxTime: "18:30:00",
      axisFormat: 'HH:mm',
      timeFormat: 'HH:mm',
      slotLabelFormat: {
        hour: '2-digit',
        minute: '2-digit',
        omitZeroMinute: false,
        meridiem: false,
        hour12: false
      },
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: "newReservation"
      },
      customButtons: {
        newReservation: {
          text: 'New Reservation',
          click: me.make_new_reservation
        }
      },
      events: (opts, callback)=>{
        me.get_events(opts, callback)
      },
			selectable: true,
  
    });

    this.calendar.render();
  };

  make_new_reservation(){
    window.location.href = "/smart-fm/facilities-service-reservation/new";
  }

  get_events(opts, callback){
    var me = this;
    console.log(opts);
    var start = frappe.datetime.get_datetime_as_string(opts.start);
    var end = frappe.datetime.get_datetime_as_string(opts.end);

    frappe.call({
      method:"erpnext.smart_fm.doctype.facilities_service_reservation.facilities_service_reservation.get_events",
      args:{
        start:start,
        end:end,
        filters:[]
      },
      callback:(r)=>{
        var events = me.prepare_events(r.message);
        callback( events )
      }
    })
  }

  prepare_events(events){
    $.each(events, (i,d)=>{
      d.title = d.service;
      d.start = d.from_time;
      d.end = d.to_time;
      d.allDay = d.all_day; 
      d.id = d.name
    });

    console.log(events)
    return events
  }

  get required_libs() {
		let assets = [
			"https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.js"
		];
		return assets;
	}

  load_library(){
    return new Promise((resolve, reject) => {
      frappe.require(this.required_libs, resolve);
    })
  }
}

frappe.calendar = new FacilityCalendar("#calendar");