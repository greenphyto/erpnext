frappe.ui.form.on('Repeat Harvest Group', {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('View Harvest Items'), () => {
				frappe.set_route('List', 'Repeat Harvest Item', {
					repeat_harvest_group: frm.doc.name
				});
			});
		}
	}
});
