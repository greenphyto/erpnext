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
	hide_sidebar: true,
	before_render: (calendar)=>{
		calendar.custom = new FacilitiesCards(calendar);
	}
};

class FacilitiesCards{
	constructor(calendar){
		this.main = calendar;
		this.page = this.main.page;
		console.log("add new custom");
		this.setup_container();
		this.get_data();
		this.setup_cards()
	}

	get_data(){
		this.data = [
			{
				name:"Game Board",
				available:3,
				rented:3,
				status:"Partially Rent",
				status_color: "#fd8f00"
			},
			{
				name:"Meeting Room B23",
				available:0,
				rented:1,
				status:"Rented",
				status_color: "#a22ce9"
			},
			{
				name:"Table Tennis",
				available:5,
				rented:0,
				status:"Available",
				status_color: "#00bf00"
			},
			{
				name:"Game Board",
				available:3,
				rented:3,
				status:"Partially Rent",
				status_color: "#fd8f00"
			},
			{
				name:"Meeting Room B23",
				available:0,
				rented:1,
				status:"Rented",
				status_color: "#a22ce9"
			},
			{
				name:"Table Tennis",
				available:5,
				rented:0,
				status:"Available",
				status_color: "#00bf00"
			},
			{
				name:"Game Board",
				available:3,
				rented:3,
				status:"Partially Rent",
				status_color: "#fd8f00"
			},
			{
				name:"Meeting Room B23",
				available:0,
				rented:1,
				status:"Rented",
				status_color: "#a22ce9"
			},
			{
				name:"Table Tennis",
				available:5,
				rented:0,
				status:"Available",
				status_color: "#00bf00"
			}
		]
	}

	setup_container(){
		this.container = $(`<div class="custom-calendar-container" id='facilities-calendar'></div>`)
		this.page.wrapper.find(".layout-main-section-wrapper").prepend(this.container);
		this.wrapper = $(`
		<div class="facility-cards">
			<div class="left-tools">
				<div class="show-all">Show All</div>
				<div class="clear-selected">clear</div>
			</div>
			<div class="list-controller">
				<div class="btn btn-default icon-btn left-arrow">
					<svg class="icon  icon-sm" style="">
						<use class="" href="#icon-left"></use>
					</svg>
				</div>
			</div>
			<div class="card-list-wrapper" id="scrollableElement">
				<div class="card-list" id="innerContent" ></div>
			</div>
			<div class="list-controller">
				<div class="btn btn-default icon-btn right-arrow ">
					<svg class="icon  icon-sm" style="">
						<use class="" href="#icon-right"></use>
					</svg>
				</div>
			</div>
		</div>`)
		this.wrapper.appendTo(this.container);
		this.page.wrapper.find(".layout-main-section").appendTo(this.container);

		this.card_list = this.wrapper.find(".card-list");
	}

	setup_ui(){

	}

	get_card(data){
		var card = $(`
			<div>
				<div class="facility-card frappe-card">
					<div class="top-detail">
						<div class="status" style="color: ${data.status_color};">${data.status}</div>
						<div class="facility-name">${data.name}</div>
					</div>
					<div class="bottom-detail">
						<div class="available">Available: <span class="count">${data.available}</span></div>
						<div class="rented">Rented:<span class="count">${data.rented}</span></div>
						<div class="blank"></div>
					</div>
				</div>
			</div>
		`)

		// setup controller: click etc

		return card;
	}

	setup_cards(){
		var me = this;
		$.each(this.data, (i, d)=>{
			var card = me.get_card(d);
			me.card_list.append(card);
		})	

		frappe.utils.make_dragable('scrollableElement', 'innerContent');
	}
}





