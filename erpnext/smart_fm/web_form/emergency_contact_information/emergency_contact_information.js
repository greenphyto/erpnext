frappe.ready(function() {
	// bind events here
	frappe.validate_phone_field([
		'phone_number', 
		'emergency_phone_1', 'emergency_alt_phone_1',
		'emergency_phone_2', 'emergency_alt_phone_2'
	]);

	frappe.validate_email_field([
		'email_address', 
		'emergency_email_1', 'emergency_email_2',
	]);

})