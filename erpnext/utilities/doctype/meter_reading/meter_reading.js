// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Meter Reading', {
	type_of_meter: function(frm) {
		if (frm.doc.type_of_meter=="Electricity"){
			frm.set_currency_labels(['current_reading'], "kWh");
		}else if (frm.doc.type_of_meter=="Water"){
			frm.set_currency_labels(['current_reading'], "m3");
		}else if (frm.doc.type_of_meter=="Gas"){
			frm.set_currency_labels(['current_reading'], "kWh");
		}
	}
});
