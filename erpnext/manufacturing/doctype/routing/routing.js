// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Routing', {
	refresh: function(frm) {
		frm.trigger("display_sequence_id_column");
	},

	onload: function(frm) {
		frm.trigger("display_sequence_id_column");
	},

	display_sequence_id_column: function(frm) {
		frm.fields_dict.operations.grid.update_docfield_property(
			'sequence_id', 	'in_list_view', 1
		);
	},

	calculate_operating_cost: function(frm, child) {
		var operating_cost = 0;
		if (child.calculation_type=='Per Qty'){
			operating_cost = flt(flt(child.operation_rate) * 1, precision("operating_cost", child));
		}else{
			operating_cost = flt(flt(child.operation_rate) * flt(child.time_in_mins) / 60, precision("operating_cost", child));
		}
		frappe.model.set_value(child.doctype, child.name, "operating_cost", operating_cost);
	}
});

frappe.ui.form.on('BOM Operation', {
	operation: function(frm, cdt, cdn) {
		const d = locals[cdt][cdn];

		if(!d.operation) return;

		frappe.call({
			"method": "frappe.client.get",
			args: {
				doctype: "Operation",
				name: d.operation
			},
			callback: function (data) {
				if (data.message.description) {
					frappe.model.set_value(d.doctype, d.name, "description", data.message.description);
				}

				if (data.message.workstation) {
					frappe.model.set_value(d.doctype, d.name, "workstation", data.message.workstation);
				}

				frm.events.calculate_operating_cost(frm, d);
			}
		});
	},

	workstation: function(frm, cdt, cdn) {
		const d = locals[cdt][cdn];

		if (d.workstation){
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Workstation",
					name: d.workstation
				},
				callback: function (data) {
					var opr_rate = 0;
					if (data.message.calculation_type=='Per Qty'){
						opr_rate = data.message.per_qty_rate;
					}else{
						opr_rate = data.message.hour_rate;
					}
					frappe.model.set_value(d.doctype, d.name, "operation_rate", flt(opr_rate, 2));
					frm.events.calculate_operating_cost(frm, d);
				}
			});
		}else{
			frappe.model.set_value(d.doctype, d.name, "operation_rate", 0);
			frm.events.calculate_operating_cost(frm, d);
		}
	},

	time_in_mins: function(frm, cdt, cdn) {
		const d = locals[cdt][cdn];
		frm.events.calculate_operating_cost(frm, d);
	}
});

frappe.tour['Routing'] = [
	{
		fieldname: "routing_name",
		title: "Routing Name",
		description: __("Enter a name for Routing.")
	},
	{
		fieldname: "operations",
		title: "BOM Operations",
		description: __("Enter the Operation, the table will fetch the Operation details like Hourly Rate, Workstation automatically.\n\n After that, set the Operation Time in minutes and the table will calculate the Operation Costs based on the Hourly Rate and Operation Time.")
	}
];

console.log("100")