frappe.ready(function() {
	// bind events here
	frappe.run_onload = ()=>{
		if (frappe.web_form.is_new){
			frappe.web_form.set_value("pic", frappe.session.user);
		}

		frappe.web_form.on("pic", (frm, value)=>{
			if (value){
				frappe.db.get_value("User", value, "full_name").then(r=>{ 
					if (r.message){
						console.log(frm, value, r.message.full_name)
						frappe.web_form.set_value("pic_name", r.message.full_name)
					}
				})
			}else{
				frappe.web_form.set_value("pic_name", "")
			}
		})
	};


	console.log("here 8")
	// filter template
	// get user full name

	// mapping checklist to form
	// control check/uncheck
	frappe.run_onload();
})