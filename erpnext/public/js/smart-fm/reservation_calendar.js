class FacilityCalendar{
  constructor(class_name){
    this.wrapper = $(class_name);
    this.initial_date = '2023-11-07';
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
      initialView: 'timeGridDay',
      initialDate: this.initial_date,
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: "newReservation,dayGridMonth,timeGridWeek,timeGridDay"
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
      d.title = d.name;
      d.start = d.from_time;
      d.end = d.to_time;
      d.color = "green"
    });

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

console.log(1111)