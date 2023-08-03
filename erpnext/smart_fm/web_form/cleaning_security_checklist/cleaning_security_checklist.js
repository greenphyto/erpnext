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
		console.log("here 8")
		// filter template
	
		// mapping checklist to form

		// control check/uncheck
		frappe.web_form.easy = new EasyChecklist(frappe.web_form)

	};


	frappe.run_onload();
})


class EasyChecklist{
	constructor(frm){
		this.frm = frm;
		this.wrapper_field = "easy_checklist";
		this.table_field = "checklist";
		this.init_template();
		this.setup();
	}

	init_template(){
		var me = this;
		this.template_checkbox = `
			<div class="form-check">
				<input class="check-input" type="checkbox" value="" id="flexCheckDefault">
				<label class="check-label" for="flexCheckDefault">
					Default checkbox
				</label>
			</div>
		`
		this.template_group_indicator = `
			<div class="group-indicator">
				<div class="text-label"></div>
			</div>
		
		`
		this.get_check_el = function(row_name, label, value, indent, is_group){
			var el;
			if (!is_group){
				el = $(me.template_checkbox);
				el.find('.check-label').text(label).attr("for", row_name);
				el.find('.check-input').val( cint(value) ).attr("id", row_name);
			}else{
				el = $(me.template_group_indicator);
				if (indent==0){
					el.addClass("root-group")
				};
				el.find(".text-label").text(label);
			}
			el.css("padding-left", 20*cint(indent));
			return el;
		}
	}

	setup(){
		this.setup_data();
		this.setup_wrapper();
		this.setup_element();
	}

	setup_data(){
		this.data = this.frm.doc[this.table_field] || [];
	}

	setup_wrapper(){
		this.base_wrapper = this.frm.fields_dict[this.wrapper_field].$wrapper;
	}

	setup_element(){
		this.base_wrapper.append(`
			<div class="eazy-wrapper"></div>
		`);
		this.wrapper = this.base_wrapper.find(".eazy-wrapper");
		this.render_checklist();
	}

	render_checklist(){
		var me = this;
		$.each(this.data, (i, d)=>{
			var check_el = me.get_check_el(
				d.name, 
				d.indicator, 
				d.value, 
				d.indent, 
				d.is_group
			)
			me.wrapper.append(check_el);
		})
	}


}