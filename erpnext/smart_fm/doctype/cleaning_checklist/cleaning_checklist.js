// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cleaning Checklist', {
	level_1_enable: function(frm){
		frm.cscript.load_area(frm,1);
	},
	level_2_enable: function(frm){
		frm.cscript.load_area(frm,2);
	},
	level_3_enable: function(frm){
		frm.cscript.load_area(frm,3);
	},
	level_4_enable: function(frm){
		frm.cscript.load_area(frm,4);
	},
	level_5_enable: function(frm){
		frm.cscript.load_area(frm,5);
	},
	posting_date: function(frm){
		const result = extractMonthYear(frm.doc.posting_date);
		frm.set_value("month", result.month);
		frm.set_value("year", result.year);
	}
});

$.extend(cur_frm.cscript, {
	load_area: function(frm,level){
		frappe.call({
			method:"load_area",
			doc:frm.doc,
			args:{
				level:level
			},
			callback: function(){
				frm.refresh()
			}
		})
	}
})

function extractMonthYear(dateStr) {
    const [year, month, day] = dateStr.split("-").map(Number);
    const date = new Date(year, month - 1, day); // Bulan di JS berbasis 0 (Januari = 0)
    
    const monthName = date.toLocaleString("en-US", { month: "long" }); // Nama bulan
    return { month: monthName, year: year.toString() };
}