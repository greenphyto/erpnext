frappe.ready(function() {
	// bind event to web form doc
})

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

	// filter template

	// mapping checklist to form

	// control check/uncheck
	if (frappe.web_form.in_edit_mode){
		frappe.web_form.easy = new EasyChecklist(frappe.web_form);
	}else{
		frappe.web_form.easy = new EasyChecklist(frappe.web_form, false, true);
	}

	frappe.web_form.on("template", (frm, value)=>{
		frappe.web_form.easy = new EasyChecklist(frappe.web_form, true);
	})

};


class EasyChecklist{
	constructor(frm, renew=false, read_only=false){
		this.frm = frm;
		this.read_only = read_only;
		this.wrapper_field = "easy_checklist";
		this.table_field = "checklist";
		this.load_data(renew).then(()=>{
			this.init_template();
			this.setup();
		})
	}

	load_data(renew){
		var me = this;
		return new Promise((resolve, reject) => {
			if (this.frm.doc.template){
				if (renew){
					frappe.call({
						method:"erpnext.smart_fm.doctype.cleaning_and_security_checklist.cleaning_and_security_checklist.load_template_indicator_web",
						args:{
							template: me.frm.doc.template
						},
						callback: r=>{
							if(r.message){
								r = r.message;
								console.log(r)
							}
						}
					})
				}else{
					resolve();
				}
			}else{
				frappe.web_form.doc[this.table_field] = [];
				frappe.web_form.refresh();
				resolve()
			}
		})
	}

	add_row_table(data){

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
				el.find('.check-input').prop("checked", cint(value) ).attr("id", row_name);

				if (me.read_only){
					el.find("input").prop('disabled', true);
				}
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
				d.is_group,

			)
			if (!d.is_group && !me.read_only){
				check_el.find("input").change(function(){
					me.click_checkbox(this)
				});
			}
			me.wrapper.append(check_el);
		})
	}

	click_checkbox(elem){
		var row_name = $(elem).attr("id");
		var check = elem.checked;
		var grid = frappe.web_form.fields_dict[this.table_field].grid;
		if (grid){
			var grid_row  = grid.grid_rows_by_docname[row_name];
			if (grid_row){
				grid_row.doc.value = cint(check);
				grid_row.refresh();
			}
		}
	}

}