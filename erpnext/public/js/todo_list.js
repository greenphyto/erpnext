
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
        if (doc.reference_type=="Asset Maintenance"){
            return `/app/asset-maintenance-log/${encodeURIComponent(cstr(doc.additional_reference))}`;
        }else if (doc.reference_type=="Asset Repair"){
            return `/app/asset-repair/${encodeURIComponent(cstr(doc.reference_name))}`
        }
        return `/app/todo/${encodeURIComponent(cstr(doc.name))}`;
    }
})
