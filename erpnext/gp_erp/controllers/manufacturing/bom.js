frappe.ui.form.on("BOM", {
	quantity: function(frm) {
		erpnext.bom.calculate_op_cost(frm.doc);
		erpnext.bom.calculate_total(frm.doc);
	}
});

// GP: override operation_rate instead of hour_rate
cur_frm.cscript.operation_rate = function(doc) {
	erpnext.bom.calculate_op_cost(doc);
	erpnext.bom.calculate_total(doc);
};

cur_frm.cscript.time_in_mins = cur_frm.cscript.operation_rate;

// GP: calculate_op_cost supports Per Qty / Per KG calculation types
erpnext.bom.calculate_op_cost = function(doc) {
	if (!doc.operations) return;
	var op = doc.operations;
	doc.planned_operating_cost = 0.0;
	doc.base_operating_cost = 0.0;

	for(var i=0;i<op.length;i++) {
		var operating_cost = 0;
		if (op[i].calculation_type == "Per Qty") {
			operating_cost = flt(flt(op[i].operation_rate) * flt(doc.quantity), 2);
		} else {
			operating_cost = flt(flt(op[i].operation_rate) * flt(op[i].time_in_mins) / 60, 2);
		}
		var base_operating_cost = flt(operating_cost * doc.conversion_rate, 2);
		frappe.model.set_value('BOM Operation', op[i].name, "operating_cost", operating_cost);
		frappe.model.set_value('BOM Operation', op[i].name, "base_operating_cost", base_operating_cost);
		doc.planned_operating_cost += operating_cost;
		doc.base_operating_cost += base_operating_cost;
	}
};

// GP: workstation handler supports Per Qty / Per KG / Per Hour
frappe.ui.form.on("BOM Operation", "workstation", function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.workstation) {
		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Workstation",
				name: d.workstation
			},
			callback: function (data) {
				var res = data.message;
				if (res.calculation_type == "Per Hour") {
					frappe.model.set_value(d.doctype, d.name, "base_operation_rate", res.hour_rate);
					frappe.model.set_value(d.doctype, d.name, "operation_rate",
						flt(flt(res.hour_rate) / flt(frm.doc.conversion_rate)));
					d.electrical_cost = res.hour_rate_electricity;
					d.consumable_cost = res.hour_rate_consumable;
					d.machinery_cost = 0;
					d.wages_cost = res.hour_rate_labour;
					d.rent_cost = res.hour_rate_rent;
				} else {
					frappe.model.set_value(d.doctype, d.name, "base_operation_rate", res.per_qty_rate);
					frappe.model.set_value(d.doctype, d.name, "operation_rate",
						flt(flt(res.per_qty_rate) / flt(frm.doc.conversion_rate)));
					d.electrical_cost = res.per_qty_rate_electricity;
					d.consumable_cost = res.per_qty_rate_consumable;
					d.machinery_cost = res.per_qty_rate_machinery;
					d.wages_cost = res.per_qty_rate_wages;
					d.rent_cost = 0;
				}
				frm.refresh_field("operations");
				erpnext.bom.calculate_op_cost(frm.doc);
				erpnext.bom.calculate_total(frm.doc);
			}
		});
	} else {
		frappe.model.set_value(d.doctype, d.name, "base_operation_rate", 0);
		frappe.model.set_value(d.doctype, d.name, "operation_rate", 0, 2);
		erpnext.bom.calculate_op_cost(frm.doc);
		erpnext.bom.calculate_total(frm.doc);
	}
});
