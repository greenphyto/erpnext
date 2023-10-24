
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
			return doc.reference_name;
		},
		get_label: function () {
			return __("Open", null, "Access");
		},
		get_description: function (doc) {
            return __("Open {0}", [`${__(doc.reference_type)}: ${doc.reference_name}`]);
		},
		action: function (doc) {
            frappe.set_route("Form", doc.reference_type, doc.reference_name);
		},
	},
})
