// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/selling/sales_common.js' %};

frappe.provide("erpnext.stock");
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Lazada Delivery", {
	setup(frm) {
		frm.set_indicator_formatter("item_code", function (doc) {
			return doc.docstatus === 1 || doc.qty <= doc.actual_qty ? "green" : "orange";
		});

		frm.set_query("warehouse", "items", function () {
			return erpnext.queries.warehouse(frm.doc);
		});

		frm.set_query("target_warehouse", "items", function () {
			return erpnext.queries.warehouse(frm.doc);
		});

		frm.set_query("batch_no", "items", function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			if (!d.item_code) {
				frappe.msgprint(__("Please enter Item Code first"));
				return;
			}
			return {
				query: "erpnext.controllers.queries.get_batch_no",
				filters: { item_code: d.item_code, warehouse: d.warehouse },
			};
		});

		frm.set_query("expense_account", "items", function (doc) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						report_type: "Profit and Loss",
						company: doc.company,
						is_group: 0,
					},
				};
			}
		});

		frm.set_query("cost_center", "items", function (doc) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						company: doc.company,
						is_group: 0,
					},
				};
			}
		});

		frm.set_query("set_warehouse", function (doc) {
			return {
				filters: {
					company: doc.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("set_target_warehouse", function (doc) {
			return {
				filters: {
					company: doc.company,
					is_group: 0,
				},
			};
		});
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.set_warehouse) {
			frm.set_value("set_warehouse", frappe.sys_defaults.default_warehouse || "");
		}
		if (frm.is_new() && !frm.doc.set_target_warehouse) {
			frm.set_value("set_target_warehouse", frappe.sys_defaults.default_warehouse || "");
		}
	},

	refresh(frm) {
		if (frm.doc.docstatus == 1) {
			frm.cscript.show_stock_ledger();
		}

		if (!frm.doc.is_return && frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Return"),
				function () {
					frappe.model.open_mapped_doc({
						method: "erpnext.gp_erp.doctype.lazada_delivery.lazada_delivery.LazadaDelivery.make_return",
						frm: frm,
					});
				},
				__("Create")
			);

			frm.add_custom_button(
				__("Sales Invoice"),
				function () {
					frappe.model.open_mapped_doc({
						method: "erpnext.gp_erp.doctype.lazada_delivery.lazada_delivery.LazadaDelivery.make_sales_invoice",
						frm: frm,
					});
				},
				__("Create")
			);

			frm.page.set_inner_btn_group_as_primary __("Create");
		}
	},

	customer(frm) {
		if (frm.doc.customer) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Customer",
					filters: { name: frm.doc.customer },
					fieldname: ["customer_name", "tax_id"],
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("customer_name", r.message.customer_name);
					}
				},
			});
		}
	},

	company(frm) {
		if (frm.doc.company && frm.doc.tc_name == null) {
			frappe.db.get_value("Company", frm.doc.company, "default_selling_terms").then((r) => {
				if (r.message && r.message.default_selling_terms && !frm.doc.tc_name) {
					frm.set_value("tc_name", r.message.default_selling_terms);
				}
			});
		}
	},

	set_warehouse(frm) {
		sync_warehouses(frm);
	},

	set_target_warehouse(frm) {
		sync_warehouses(frm);
	},

	taxes_and_charges(frm) {
		if (frm.doc.taxes_and_charges) {
			frappe.call({
				method: "erpnext.stock.doctype.delivery_note.delivery_note.get_taxes_and_charges",
				args: {
					taxes_and_charges: frm.doc.taxes_and_charges,
				},
				callback: function (r) {
					if (r.message) {
						frm.set_value("taxes", []);
						$.each(r.message, function (i, d) {
							var child = frm.add_child("taxes");
							$.extend(child, d);
						});
						refresh_field("taxes");
						calculate_taxes_and_totals(frm);
					}
				},
			});
		}
	},
});

frappe.ui.form.on("Lazada Delivery Item", {
	item_code(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (!d.item_code) return;

		frappe.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			args: {
				args: {
					item_code: d.item_code,
					warehouse: frm.doc.set_warehouse,
					customer: frm.doc.customer,
					currency: frm.doc.currency,
					company: frm.doc.company,
					conversion_factor: 1,
					price_list: frm.doc.selling_price_list,
				},
			},
			callback: function (r) {
				if (r.message) {
					var item = r.message;
					frappe.model.set_value(cdt, cdn, "item_name", item.item_name);
					frappe.model.set_value(cdt, cdn, "description", item.description);
					frappe.model.set_value(cdt, cdn, "uom", item.uom);
					frappe.model.set_value(cdt, cdn, "stock_uom", item.stock_uom);
					frappe.model.set_value(cdt, cdn, "conversion_factor", item.conversion_factor || 1);
					frappe.model.set_value(cdt, cdn, "price_list_rate", item.price_list_rate || 0);
					frappe.model.set_value(cdt, cdn, "rate", item.price_list_rate || 0);
					frappe.model.set_value(cdt, cdn, "expense_account", item.expense_account);
					frappe.model.set_value(cdt, cdn, "cost_center", item.cost_center);
					frappe.model.set_value(cdt, cdn, "warehouse", frm.doc.set_warehouse || item.warehouse);
					frappe.model.set_value(cdt, cdn, "target_warehouse", frm.doc.set_target_warehouse || "");
					calculate_taxes_and_totals(frm);
				}
			},
		});
	},

	qty(frm, cdt, cdn) {
		calculate_taxes_and_totals(frm);
	},

	rate(frm, cdt, cdn) {
		calculate_taxes_and_totals(frm);
	},

	uom(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (!d.uom || !d.item_code) return;

		frappe.call({
			method: "erpnext.stock.get_item_details.get_conversion_factor",
			args: {
				item_code: d.item_code,
			 uom: d.uom,
			},
			callback: function (r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, "conversion_factor", r.message.conversion_factor || 1);
					calculate_taxes_and_totals(frm);
				}
			},
		});
	},

	warehouse(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.warehouse && frm.doc.set_target_warehouse && d.warehouse === frm.doc.set_target_warehouse) {
			frappe.msgprint(__("Source Warehouse and Target Warehouse cannot be the same"));
			frappe.model.set_value(cdt, cdn, "warehouse", "");
		}
	},

	target_warehouse(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.target_warehouse && d.warehouse && d.warehouse === d.target_warehouse) {
			frappe.msgprint(__("Source Warehouse and Target Warehouse cannot be the same"));
			frappe.model.set_value(cdt, cdn, "target_warehouse", "");
		}
	},

	expense_account(frm, cdt, cdn) {
		if (erpnext.is_perpetual_inventory_enabled(frm.doc.company)) {
			const d = locals[cdt][cdn];
			frm.update_in_all_rows("items", "expense_account", d.expense_account);
		}
	},

	cost_center(frm, cdt, cdn) {
		if (erpnext.is_perpetual_inventory_enabled(frm.doc.company)) {
			const d = locals[cdt][cdn];
			frm.update_in_all_rows("items", "cost_center", d.cost_center);
		}
	},
});

function sync_warehouses(frm) {
	if (!frm.is_dirty()) return;
	if (!frm.doc.items) return;

	(frm.doc.items || []).forEach((row) => {
		if (frm.doc.set_target_warehouse) {
			frappe.model.set_value(row.doctype, row.name, "target_warehouse", frm.doc.set_target_warehouse);
		}
	});
}

function calculate_taxes_and_totals(frm) {
	var total = 0;
	var total_qty = 0;

	(frm.doc.items || []).forEach((d) => {
		d.amount = flt(d.qty) * flt(d.rate);
		d.stock_qty = flt(d.qty) * flt(d.conversion_factor);
		d.base_amount = d.amount * flt(frm.doc.conversion_rate);
		d.base_rate = d.rate * flt(frm.doc.conversion_rate);
		total += d.amount;
		total_qty += d.stock_qty;
	});

	frm.set_value("total", total);
	frm.set_value("base_total", total * flt(frm.doc.conversion_rate));
	frm.set_value("total_qty", total_qty);

	var tax_total = 0;
	(frm.doc.taxes || []).forEach((t) => {
		if (t.rate) {
			t.tax_amount = total * flt(t.rate) / 100;
			t.base_tax_amount = t.tax_amount * flt(frm.doc.conversion_rate);
		}
		tax_total += flt(t.tax_amount);
	});

	frm.set_value("total_taxes_and_charges", tax_total);
	frm.set_value("base_total_taxes_and_charges", tax_total * flt(frm.doc.conversion_rate));
	frm.set_value("grand_total", total + tax_total);
	frm.set_value("base_grand_total", (total + tax_total) * flt(frm.doc.conversion_rate));

	refresh_field("items");
	refresh_field("taxes");
}
