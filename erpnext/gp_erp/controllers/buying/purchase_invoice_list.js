frappe.listview_settings["Purchase Invoice"] = {
    onload(listview) {
        listview.page.add_inner_button(__('Pull AI Invoice'), () => {
            frappe.call({
                method: "erpnext.controllers.erp.read_email_inbox_enquee",
                freeze: true,
                freeze_message: __("Processing...")
            }).then(r => {
                frappe.msgprint("Pull Email is running now");
                listview.refresh();
            });
        });
    }
};
