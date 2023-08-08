// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Checklist', {
	refresh: function(frm) {
		if (frm.is_new()){
			frm.set_value("pic", frappe.session.user);
		}

		// filter enable template only
		frm.set_query("template", ()=>{
			return {
				filters:{
					enable: 1
				}
			}
		})

		frm.cscript.refresh_tree_view()
	},
	template: function(frm){
		frm.cscript.load_template()
	}
});

$.extend(cur_frm.cscript, {
	load_template: function(){
		if (!this.frm.doc.template){
			return;
		};

		frappe.call({
			method:"load_template_indicator",
			doc: this.frm.doc,
			callback: function(){
				cur_frm.refresh();
			}
		})
	},
	refresh_tree_view: function(){
		var frm = this.frm;
		$.each(frm.doc.checklist, (i, row)=>{
			frm.cscript.change_indent_view(row.doctype, row.name);
		})
	},
	change_indent_view: function(cdt,cdn){
		var row = locals[cdt][cdn];
		if (!row) return;
		var selector = `.grid-row[data-name="${row.name}"] .grid-static-col[data-fieldname="indicator"]`;
		if (! $(selector).length ){
			return;
		}
		var el = $(selector)[0];
		var padding = 20;
		var pad_left = padding * cint(row.indent);
		if (pad_left){
			el.style.setProperty("padding-left", `${pad_left}px`, "important");
		}
		if (cint(row.is_group)){
			el.style.setProperty("font-weight", `bold`, "important");
		}else{
			el.style.setProperty("font-weight", ``);
		}
	}
})