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
        timeFormat: 'HH:mm',
		slotEventOverlap: false,
		slotDuration: '00:15:00',
		slotMinTime: "06:00:00",
		slotMaxTime: "18:30:00",
		axisFormat: 'HH:mm',
		// slotLabelFormat: {
		// 	hour: '2-digit',
		// 	minute: '2-digit',
		// 	// omitZeroMinute: false,
		// 	// meridiem: false,
		// 	hour12: false
		// },
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
		this.setup_container();
		this.get_main_data();
	}
	
	get_main_data(){
		var me = this;
		me.get_data().then(r=>{
			me.data = r;
			me.setup_cards()
			me.setup_ui();
		})
	}

	setup_container(){
		this.container = $(`<div class="custom-calendar-container" id='facilities-calendar'></div>`)
		this.page.wrapper.find(".layout-main-section-wrapper").prepend(this.container);
		this.wrapper = $(`
		<div class="facility-cards">
			<div class="left-tools">
				<a class="show-all">Show All</a>
				<a class="clear-selected">clear</a>
			</div>
			<div class="list-controller hidden">
				<div class="btn btn-default icon-btn left-arrow" style="display: none;">
					<svg class="icon  icon-sm" style="">
						<use class="" href="#icon-left"></use>
					</svg>
				</div>
			</div>
			<div class="card-list-wrapper" id="scrollableElement">
				<div class="card-list" id="innerContent" ></div>
			</div>
			<div class="list-controller hidden">
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
		this.card_list_wrapper = this.wrapper.find(".card-list-wrapper");
	}

	setup_ui(){
		var me = this;
		var travel_size = 244;
		if (this.card_list_wrapper.width()<this.card_list.width()){
			this.wrapper.find(".list-controller").removeClass("hidden");
		}
		// click arrow
		this.wrapper.find(".left-arrow").click(()=>{
			me.card_list_wrapper.addClass("scroll-smooth");
			me.card_list_wrapper.scrollLeft(me.card_list_wrapper.scrollLeft()+travel_size*-1);
			setTimeout(()=>{
				me.card_list_wrapper.removeClass("scroll-smooth");
			}, 200);
		});
		this.wrapper.find(".right-arrow").click(()=>{
			me.card_list_wrapper.addClass("scroll-smooth");
			me.card_list_wrapper.scrollLeft(me.card_list_wrapper.scrollLeft()+travel_size*1);
			setTimeout(()=>{
				me.card_list_wrapper.removeClass("scroll-smooth");
			}, 200);
		});

		this.wrapper.find(".clear-selected").click(()=>{
			me.filter_service("", true);
			frappe.show_alert("Clear filter", 2);
		})
		
		this.wrapper.find(".show-all").click(()=>{
			me.show_all();
		})

		this.card_list_wrapper.on("scroll", ()=>{
			if (me.card_list_wrapper.scrollLeft()<10){
				me.wrapper.find(".left-arrow").hide();
			}else{
				me.wrapper.find(".left-arrow").show();
			}
		})
	}

	get_card(data){
		var me = this;
		var card = $(`
			<div class="facility-card frappe-card" service="${data.name}">
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
		`)

		// setup controller: click etc
		card.click(function(e){
			var el = $(this);
			var service = el.attr("service");
			me.filter_service(service);
			if (me.all_dialog){
				me.all_dialog.hide();
			}
		})

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

	filter_service(service, remove=false){
		var me = this;
		var filters = [['Facilities Service Reservation', 'service', '=', service]];
		me.main.list_view.filter_area.remove_filters(filters);
		if (!remove){
			me.main.list_view.filter_area.add(filters, true);
			frappe.show_alert(__(`Set filter to <b>${service}</b>`), 2)
		}

		var cal_toolbar = this.main.$cal.find(".fc-toolbar .fc-left");
		var title = cal_toolbar.find(cal_toolbar.find(".select-service"));
		if (!service){
			title.remove();
		}
		if (!title.length){
			cal_toolbar.append(`<div class="select-service">${service}</div>`)
		}else{
			title.text(service)
		}
	}

	show_all(){
		var me = this;
		if (!me.all_dialog){
			me.all_dialog = new frappe.ui.Dialog({
				title: 'Select Facility',
				fields: [
					{
						label: 'Filters',
						fieldname: 'sec_break',
						fieldtype: 'Section Break'
					},
					{
						label: 'Search',
						fieldname: 'facility_service',
						fieldtype: 'Data',
						onchange:()=>{
							me.update_dialog_list();
						} 
					},
					{
						label: '',
						fieldname: 'sec_break3',
						fieldtype: 'Column Break'
					},
					{
						label: 'Status',
						fieldname: 'status',
						fieldtype: 'Select',
						options:"\nAvailable\nPartially Rented\nAll Rented",
						onchange:()=>{
							me.update_dialog_list();
						}
					},
					{
						label: 'Facilties Service',
						fieldname: 'sec_break2',
						fieldtype: 'Section Break'
					},
					{
						label: '',
						fieldname: 'ht',
						fieldtype: 'HTML'
					}
				],
				size: 'large', // small, large, extra-large 
			});

		}
		
		me.all_dialog.show();

		var wrapper = this.all_dialog.fields_dict.ht.$wrapper;
		wrapper.empty().addClass("facilities-calendar-dialog");
		wrapper.append("<div class='wrapper-list'></div>")

		me.render_dialog_list({}, true);
	}

	update_dialog_list(){
		var load = false;
		var filters = {};

		var service_field = this.all_dialog.fields_dict.facility_service;
		if (service_field.old_value != service_field.value){
			service_field.old_value = service_field.value;
			load = true
		}

		var status_field = this.all_dialog.fields_dict.status;
		if (status_field.old_value != status_field.value){
			status_field.old_value = status_field.value;
			load = true
		}
		if (status_field.value) filters.status = status_field.value;
		if (service_field.value) filters.name = ['like', "%"+service_field.value+"%"];

		if (load){
			this.render_dialog_list(filters, true);
		}
	}

	render_dialog_list(filters={}, clear=false){
		var me = this;
		var temp = this.all_dialog.fields_dict.ht.$wrapper;
		var wrapper = temp.find(".wrapper-list");
		wrapper.hide();
		if (clear){
			wrapper.empty();
		}
		this.get_data(filters).then(r=>{
			var data= r;
	
			$.each(data, (i, d)=>{
				var card = this.get_card(d);
				wrapper.append(card);
			})

			setTimeout(()=>{
				wrapper.show();
			}, 100);
		})
	}

	get_data(filters){
		return new Promise((resolve, reject) => {
			frappe.call({
				method:"erpnext.smart_fm.doctype.facilities_service_reservation.facilities_service_reservation.get_facilities_list",
				args:{
					filters:filters
				},
				callback: r=>{
					resolve(r.message || [])
				}
			})
		})
	}
}





