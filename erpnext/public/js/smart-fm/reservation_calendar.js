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
    this.calendar = new FullCalendar.Calendar(this.wrapper[0], {
      initialView: 'timeGridDay',
      initialDate: this.initial_date,
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: ""
      },
      events: [
        {
          title: 'All Day Event',
          start: '2023-11-01'
        },
        {
          title: 'Long Event',
          start: '2023-11-07',
          end: '2023-11-10'
        },
        {
          groupId: '999',
          title: 'Repeating Event',
          start: '2023-11-09T16:00:00'
        },
        {
          groupId: '999',
          title: 'Repeating Event',
          start: '2023-11-16T16:00:00'
        },
        {
          title: 'Conference',
          start: '2023-11-11',
          end: '2023-11-13'
        },
        {
          title: 'Meeting',
          start: '2023-11-12T10:30:00',
          end: '2023-11-12T12:30:00'
        },
        {
          title: 'Lunch',
          start: '2023-11-12T12:00:00'
        },
        {
          title: 'Meeting',
          start: '2023-11-12T14:30:00'
        },
        {
          title: 'Birthday Party',
          start: '2023-11-13T07:00:00'
        },
        {
          title: 'Click for Google',
          url: 'https://google.com/',
          start: '2023-11-28'
        }
      ]});

    this.calendar.render();
  };

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