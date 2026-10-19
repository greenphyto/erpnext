frappe.ui.form.on('Repeat Harvest Item', {
	refresh(frm) {
		if (frm.doc.work_order) {
			frm.add_custom_button(__('View Work Order'), () => {
				frappe.set_route('Form', 'Work Order', frm.doc.work_order);
			});
		}
	}
});
