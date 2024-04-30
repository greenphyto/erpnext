frappe.ready(function() {
	// bind events here
	console.log("custom JS")

	// set disable edit when submit
	var doc = frappe.web_form.doc;

	if (doc.docstatus != 0){
		$(".edit-button").hide();
	}
})