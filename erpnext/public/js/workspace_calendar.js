console.log("Custom calendar")

frappe.run_calendar = function (wrapper, calendar_name){
    var opts = {};

    opts.parent = wrapper;
    opts.single_column = true;
    opts.title = "Calendar Custom"
    opts.hide_sidebar = true

    var page = frappe.ui.make_app_page(opts)
    frappe.calendar = new CustomCalendar({
        doctype: "ToDo",
        parent: wrapper,
        hide_sidebar: 1,
        calendar_use_name: calendar_name,
        hide_sort_selector: 1,
        can_create: 0,
        field_map: {
			id: "name",
			start: "creation",
			end: "creation",
			allDay: "1",
			convertToUserTz: "convert_to_user_tz",
		}
    });
}

class CustomCalendar extends frappe.views.CalendarView{
    constructor(opts){
        opts.parent.find(".page-head").addClass("hidden");
        super(opts);
    }
    setup_page(){
        this.can_create = 0;
        super.setup_page();
    }

    before_render() {
        this.calendar_name = this.calendar_use_name;
		super.before_render();
        this.parent.find(".page-head").addClass("hidden");
    }

    set_menu_items(){

    }

    add_customization_buttons(){

    }

    setup_view_menu(){
        
    }

    render_header(){

    }

    setup_page_head(){

    }
}