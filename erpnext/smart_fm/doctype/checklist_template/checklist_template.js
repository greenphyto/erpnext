// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Checklist Template', {
	refresh: function(frm) {
		frm.cscript.refresh_tree_view();
	}
});

frappe.ui.form.on('Indicator List', {
	indent: function(frm, cdt, cdn) {
		frm.cscript.change_indent_view(cdt, cdn);
	},
	is_group: function(frm, cdt, cdn){
		frm.cscript.change_indent_view(cdt, cdn);
	}
});

$.extend(cur_frm.cscript, {
	refresh_tree_view: function(){
		var frm = this.frm;
		$.each(frm.doc.indicators, (i, row)=>{
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

console.log("controller here")