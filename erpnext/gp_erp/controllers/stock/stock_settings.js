frappe.ui.form.on('Stock Settings', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__('Send Missing Item Price'), function() {
				frappe.confirm(
					"Send Missing Item Price notification email now?",
					() => {
						frappe.call({
							method: "erpnext.stock.doctype.stock_settings.stock_settings.send_missing_item_price_notification",
							freeze: true,
							freeze_message: "Sending notification...",
							callback(r) {
								if (!r.exc) {
									frappe.show_alert({
										message: "Missing Item Price notification sent successfully.",
										indicator: "green"
									});
								}
							}
						});
					}
				);
			});
		}
	}
});
