console.log("here form")

frappe.ready(function() {
	frappe.set_default_web_form([
		"email as email_address", 
		"full_name as full_name"
	])

	// bind events here
	console.log("here form")
	frappe.web_form.on("service", (frm, value)=>{
		if (value){
			frappe.set_value_web_form("Facility Service", {"name":value}, [
				"available_qty as quantity_available",
				"description",
				"image as preview_link" ,
				"status as service_status"
			]).then(r=>{
				// set image service
				frappe.render_image_field("service-image", r.preview_link);
			})
		}
	})
})

