console.log("Here custom calendar")

frappe.run_calendar = function (){
    var opts = {};
    var wrapper = $('.ce-paragraph');
    // wrapper.append(`
    // <div class='page'>
    //     <div class="container">
    //         <div class="layout-main-section">
    //             <div class="page-form"></div>
    //         </div>
    //     </div>
    // </div>`)
    opts.parent = wrapper;
    opts.single_column = true;
    opts.title = "Calendar Custom"
    opts.hide_sidebar = true

    // wrapper.page = wrapper.find(".page");
    // wrapper.page.container = wrapper.find(".container");
    // wrapper.page.main = wrapper.find(".layout-main-section");
    // wrapper.page.page_form = wrapper.find(".page-form");
    frappe.ui.make_app_page(opts)
    frappe.calendar = new CustomCalendar({
        doctype: "ToDo",
        parent: wrapper,
        hide_sidebar: 1,
        calendar_use_name:"default",
        hide_sort_selector: 1,
        can_create: 0
    });
}

class CustomCalendar extends frappe.views.CalendarView{
    setup_page(){
        this.can_create = 0;
        super.setup_page();
    }

    before_render() {
        this.calendar_name = this.calendar_use_name;
		super.before_render();
    }

    set_menu_items(){

    }

    add_customization_buttons(){

    }

    setup_view_menu(){
        
    }
}