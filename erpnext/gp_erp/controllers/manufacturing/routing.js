frappe.ui.form.on('Routing', {
	calculate_operating_cost: function(frm, child) {
		var operating_cost = 0;
		if (child.calculation_type == 'Per Qty') {
			operating_cost = flt(flt(child.operation_rate) * 1, precision("operating_cost", child));
		} else {
			operating_cost = flt(flt(child.operation_rate) * flt(child.time_in_mins) / 60, precision("operating_cost", child));
		}
		frappe.model.set_value(child.doctype, child.name, "operating_cost", operating_cost);
	}
});

frappe.ui.form.on('BOM Operation', {
	workstation: function(frm, cdt, cdn) {
		const d = locals[cdt][cdn];
		if (d.workstation) {
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Workstation",
					name: d.workstation
				},
				callback: function (data) {
					var opr_rate = 0;
					if (data.message.calculation_type == 'Per Qty') {
						opr_rate = data.message.per_qty_rate;
					} else {
						opr_rate = data.message.hour_rate;
					}
					frappe.model.set_value(d.doctype, d.name, "operation_rate", flt(opr_rate, 2));
					frm.events.calculate_operating_cost(frm, d);
				}
			});
		} else {
			frappe.model.set_value(d.doctype, d.name, "operation_rate", 0);
			frm.events.calculate_operating_cost(frm, d);
		}
	},
});
