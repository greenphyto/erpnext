
// overide and extend frappe's todo_list.js 
frappe.provide(`frappe.listview_settings.ToDo`)
$.extend(frappe.listview_settings["ToDo"], {
    add_fields: [...frappe.listview_settings["ToDo"]['add_fields'], "additional_reference"],
    refresh: function (me) {
		if (me.todo_sidebar_setup) return;

		// add assigned by me
		me.page.add_sidebar_item(
			__("Assigned By Me"),
			function () {
				me.filter_area.add([[me.doctype, "assigned_by", "=", frappe.session.user]]);
			},
			'.list-link[data-view="Kanban"]'
		);

		me.todo_sidebar_setup = true;
	},
    get_form_link: function(doc){
        if (doc.reference_type && doc.reference_name){
            return frappe.utils.get_form_link(doc.reference_type, doc.reference_name)
        }else{
            return `/app/todo/${encodeURIComponent(cstr(doc.name))}`;
        }
    },
    button: {
		show: function (doc) {
			return true;
		},
		get_label: function () {
			return __("Open", null, "Access");
		},
		get_description: function (doc) {
            return __("Open {0}", [`${__(doc.reference_type || "ToDo")}: ${doc.reference_name || doc.name}`]);
		},
		action: function (doc) {
			if (!doc.reference_name){
				frappe.set_route("Form", "ToDo", doc.name);
			}else{
				frappe.set_route("Form", doc.reference_type, doc.reference_name);
			}
		},
	},
	get_indicator: function(doc) {
		if (doc.status=="Planned") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (doc.status=="Completed") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (doc.status=="Cancelled") {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status=="Overdue") {
			return [__(doc.status), "red", "status,=," + doc.status];
		}
	}
})
