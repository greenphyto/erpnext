frappe.ui.form.on("Work Order", {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1 && frm.doc.status != "Closed") {
			frm.trigger("show_foms_status");
		}

		if (frm.doc.status != "Closed") {
			if (cint(frm.doc.material_returned) == 0) {
				frm.add_custom_button(__("Scrap Components"), function() {
					frm.trigger("create_stock_return_entry");
				}).addClass("btn-primary");
			}
		}
	},

	show_foms_status: function(frm) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.work_order.work_order.get_foms_task_status",
			args: {
				work_order: frm.doc.name,
				item_code: frm.doc.production_item,
				foms_work_order: frm.doc.foms_work_order
			},
			callback: function(r) {
				if (!r.message) return;
				const tasks = r.message;
				const fomsTasksUrl = `https://foms.greenphyto.com/user/operations/overall-tasks?isYourTask=false&lotId=${frm.doc.foms_lot_name}&page=1`;
				const checkIcon = '<span style="color:green;font-weight:bold;">&#10003;</span>';
				const emptyBox = '<span style="color:#aaa;">&#9744;</span>';
				let taskHtml = tasks.map(t => {
					const icon = t.foms_status ? checkIcon : emptyBox;
					return `<span style="margin-right:12px;">${__(t.operation)} ${icon}</span>`;
				}).join('');
				const warnings = tasks
					.filter(t => cint(t.pending))
					.map(t => `<div class="alert alert-warning" style="margin:4px 0;padding:6px 10px;">
						<strong>${__("Warning!")}</strong> ${__(t.operation)} ${__("is not syncing yet to ERP!")}
					</div>`).join('');
				const hasWarning = tasks.some(t => cint(t.pending));
				const warningLink = hasWarning
					? `<div style="margin-top: 10px;margin-left: 10px;font-size: 0.94em;">
						<a href="${fomsTasksUrl}" target="_blank" rel="noopener noreferrer"><u>${__("Open tasks to FOMS")}</u></a>
					</div>`
					: "";
				const html = `
					<div style="padding:8px 0;">
						<div style="margin-bottom:6px;">
							<strong>${__("FOMS Task")}:</strong>&nbsp;${taskHtml}
						</div>
						${warnings}
						${warningLink}
					</div>`;
				let section = frm.dashboard.add_section(html, __("Foms Status"));
				frm.dashboard.progress_area.wrapper.after(section.parent());
			}
		});
	},

	create_stock_return_entry: function(frm) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.work_order.work_order.make_scrap_materials",
			args: {
				"work_order": frm.doc.name,
			},
			callback: function(r) {
				if (r.message) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},
});

erpnext.work_order = {
	set_custom_buttons: function(frm) {
		// GP: default implementation extended elsewhere
	},
	calculate_cost: function(doc) {
		if (doc.operations) {
			var op = doc.operations;
			doc.planned_operating_cost = 0.0;
			for (var i = 0; i < op.length; i++) {
				var planned_operating_cost = 0;
				if (op[i].calculation_type == "Per Hour") {
					planned_operating_cost = flt(flt(op[i].operation_rate) * flt(op[i].time_in_mins) / 60, 2);
				} else {
					planned_operating_cost = flt(flt(op[i].operation_rate) * doc.gross_weight, 2);
				}
				frappe.model.set_value('Work Order Operation', op[i].name,
					"planned_operating_cost", planned_operating_cost);
				doc.planned_operating_cost += planned_operating_cost;
			}
		}
	},
	get_workstation_cost: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.workstation) {
			frappe.db.get_doc("Workstation", d.workstation).then(doc => {
				d.version = doc.version || 1;
				if (in_list(["Per KG", "Per Qty"], doc.calculation_type)) {
					d.electrical_cost = doc.per_qty_rate_electricity;
					d.consumable_cost = doc.per_qty_rate_consumable;
					d.machinery_cost = doc.per_qty_rate_machinery;
					d.wages_cost = doc.per_qty_rate_wages;
					d.rent_cost = 0;
				} else {
					d.electrical_cost = doc.hour_rate_electricity;
					d.consumable_cost = doc.hour_rate_consumable;
					d.machinery_cost = 0;
					d.wages_cost = doc.hour_rate_labour;
					d.rent_cost = doc.hour_rate_rent;
				}
				erpnext.work_order.calculate_cost_rate(frm, cdt, cdn);
				frm.refresh_field("operations");
			});
		} else {
			d.electrical_cost = 0;
			d.consumable_cost = 0;
			d.machinery_cost = 0;
			d.wages_cost = 0;
			d.rent_cost = 0;
		}
		erpnext.work_order.calculate_cost_rate(frm, cdt, cdn);
		frm.refresh_field("operations");
	},
	calculate_cost_rate: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		var opr_rate = d.electrical_cost + d.consumable_cost + d.machinery_cost + d.wages_cost + d.rent_cost;
		frappe.model.set_value(cdt, cdn, "operation_rate", opr_rate);
		erpnext.work_order.calculate_cost(frm.doc);
	},
};

frappe.ui.form.on("Work Order Operation", {
	workstation: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.workstation) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Workstation",
					filters: { name: d.workstation },
					fieldname: ["hour_rate", "calculation_type", "per_qty_rate"]
				},
				callback: function(data) {
					if (data.calculation_type == "Per Hour") {
						frappe.model.set_value(d.doctype, d.name, "operation_rate", data.message.hour_rate);
					} else {
						frappe.model.set_value(d.doctype, d.name, "operation_rate", data.message.per_qty_rate);
					}
					erpnext.work_order.calculate_cost(frm.doc);
				}
			});
		}
	},
	enable_cost_editing: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.enable_cost_editing) {
			frappe.model.set_value(cdt, cdn, "version", "Custom");
		} else {
			erpnext.work_order.get_workstation_cost(frm, cdt, cdn);
		}
	},
	electrical_cost: function(frm, cdt, cdn) { erpnext.work_order.calculate_cost_rate(frm, cdt, cdn); },
	consumable_cost: function(frm, cdt, cdn) { erpnext.work_order.calculate_cost_rate(frm, cdt, cdn); },
	machinery_cost: function(frm, cdt, cdn) { erpnext.work_order.calculate_cost_rate(frm, cdt, cdn); },
	wages_cost: function(frm, cdt, cdn) { erpnext.work_order.calculate_cost_rate(frm, cdt, cdn); },
	rent_cost: function(frm, cdt, cdn) { erpnext.work_order.calculate_cost_rate(frm, cdt, cdn); },
});
