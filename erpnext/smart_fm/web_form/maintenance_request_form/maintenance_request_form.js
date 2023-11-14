frappe.ready(function() {
	// bind events here
	frappe.web_form.on("attachment", ()=>{
		frappe.web_form.render_image("preview", "attachment");
	});
	frappe.web_form.render_image("preview", "attachment");
})