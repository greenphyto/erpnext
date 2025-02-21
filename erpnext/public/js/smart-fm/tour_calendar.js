class TourCalendar{
  constructor(class_name){
    this.wrapper = $(class_name);
    this.initial_date = new Date();
    this.filter_values = [];
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
        right: "filterTour newTour"
      },
      customButtons: {
        newTour: {
          text: 'New Tour',
          click: me.make_new_tour
        },
        filterTour: {
          text: 'Filter',
          click: me.filter_tour
        }
      },
      events: (opts, callback)=>{
        me.get_events(opts, callback)
      },
      eventDidMount: (info)=>{
        const title = info.el.querySelector('.fc-event-title');
        title.innerHTML = info.event.title;
      },
			selectable: true,
  
    });

    this.calendar.render();
  };

  make_new_tour(){
      window.location.href = "/menu/tour-protocol-checklist/new";
  }

  filter_tour(){
    var me = frappe.calendar;
    if (!this.filters){
      var d = new frappe.ui.Dialog({
        title: __(`Filter`),
        fields: [
          {
            "label" : "Group Name",
            "fieldname": "name",
            "fieldtype": "Autocomplete",
            "default": '',
            'get_query':()=>{
              return {
                query: "erpnext.smart_fm.doctype.tour_protocol_checklist.tour_protocol_checklist.get_group",
              }
            }
          }
        ],
        primary_action: function(data) {
          d.hide();
          if (data.name){
            me.filter_values = [['name', '=', data.name]];
          }else{
            me.filter_values = [];
          }
          me.calendar.refetchEvents();
        },
        primary_action_label: __('Submit'),
        secondary_action: function(){
          d.hide();
        },
        secondary_action_label: __("Close"),
      });
      this.filters = d;
      // modal-dialog-scrollable
      this.filters.show();
      // remove scrollable class
      this.filters.$wrapper.find(".modal-dialog").removeClass("modal-dialog-scrollable");
    }else{
      this.filters.show();
    }
  }

  get_events(opts, callback){
    var me = this;
    var start = frappe.datetime.get_datetime_as_string(opts.start);
    var end = frappe.datetime.get_datetime_as_string(opts.end);

    frappe.call({
      method:"erpnext.smart_fm.doctype.tour_protocol_checklist.tour_protocol_checklist.get_events",
      args:{
        start:start,
        end:end,
        filters:me.filter_values
      },
      callback:(r)=>{
        var events = me.prepare_events(r.message);
        callback( events )
      }
    })
  }

  prepare_events(events){
    const style_map = {
      Issued: "orange",
      Accepted: "blue",
      Started: "green",
      Finished: "purple",
      Cancelled: "grey",
      Rejected: "red",
    };
    $.each(events, (i,d)=>{
      d.title = d.group_name;
      d.start = d.start_time;
      d.end = d.end_time;
      d.allDay = d.all_day; 
      d.id = d.name;
      d.description = "Booked by " + d.full_name;
      d.backgroundColor = style_map[d.status];
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

frappe.calendar = new TourCalendar("#calendar");