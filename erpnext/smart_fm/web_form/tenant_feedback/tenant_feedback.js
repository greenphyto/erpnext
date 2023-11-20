frappe.ready(function() {
	// bind events here
	frappe.validate_phone_field(['phone_number'])
	frappe.validate_email_field(['email_address']);

})