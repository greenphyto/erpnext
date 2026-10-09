frappe.ui.form.on("Job Card", {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1 && frm.doc.status != "Completed") {
			frm.add_custom_button(__("Scrap Materials"), function() {
				frappe.call({
					method: "erpnext.manufacturing.doctype.work_order.work_order.make_scrap_materials",
					args: {
						"work_order": frm.doc.work_order,
						"percentage": 100
					},
					callback: function(r) {
						if (r.message) {
							var doclist = frappe.model.sync(r.message);
							frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
						}
					}
				});
			}, __("Create"));
		}
	}
});
