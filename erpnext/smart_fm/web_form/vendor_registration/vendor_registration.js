frappe.ready(function() {
	// bind events here
	frappe.validate_phone_field(['phone_number'])
	frappe.validate_phone_field_table('references', 'phone');
	frappe.validate_email_field_table('references', 'email');
})