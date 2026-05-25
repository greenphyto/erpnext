// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
{% include 'erpnext/stock/doctype/delivery_note/delivery_note.js' %};


cur_frm.cscript.tax_table = "Sales Taxes and Charges";
cur_frm.email_field = "contact_email";

cur_frm.add_fetch("customer", "tax_id", "tax_id");

frappe.provide("erpnext.stock");
frappe.provide("erpnext.stock.consignment_order");
frappe.provide("erpnext.accounts.dimensions");

if (!window.__consignment_order_script_loaded) {
	window.__consignment_order_script_loaded = true;

	var CO_HIDDEN_FIELDS = [
	"is_return",
	"return_against",
	"issue_credit_note",
	"is_donation",
	"is_giveaway",
	"is_replacement",
	"replacement_reason_section",
	"replacement_reason",
	"is_marketing",
	"is_production",
	"is_pledge",
	"donor_name",
	"organization_name",
	"organization_address",
	"rpl_creator",
	"set_warehouse",
	"set_posting_time",
	"delivery_completed_at",
	"delivery_completed_by",
	"signature_details_section",
	"signature",
	"attachment",
	"attachment_preview",
	"signature_by",
	"taken_at",
	"authorized_signature_section",
	"is_internal_customer",
	"represents_company",
	"inter_company_reference",
	"shipping_method_section",
	"shipping_rule",
	"mode_of_transport",
	"port_of_discharge",
	"port_of_loading",
	"carton_weight",
	"total_cartons",
	"non_package_item",
	"is_carton_order",
	"work_order",
	"transporter_info",
	"transporter",
	"driver",
	"lr_no",
	"vehicle_no",
	"transporter_name",
	"driver_name",
	"lr_date"
	];

frappe.ui.form.on("Consignment Order", {
	setup(frm) {
		frm.set_indicator_formatter("item_code", function (doc) {
			return doc.docstatus === 1 || doc.qty <= doc.actual_qty ? "green" : "orange";
		});

		erpnext.queries.setup_queries(frm, "Warehouse", function () {
			return erpnext.queries.warehouse(frm.doc);
		});
		erpnext.queries.setup_warehouse_query(frm);

		frm.set_query("project", function (doc) {
			return {
				query: "erpnext.controllers.queries.get_project_name",
				filters: {
					customer: doc.customer
				}
			};
		});

		frm.set_query("target_warehouse", "items", function () {
			return erpnext.queries.warehouse(frm.doc);
		});

		frm.set_query("expense_account", "items", function (doc) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						report_type: "Profit and Loss",
						company: doc.company,
						is_group: 0
					}
				};
			}
		});

		frm.set_query("cost_center", "items", function (doc) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						company: doc.company,
						is_group: 0
					}
				};
			}
		});
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.set_target_warehouse) {
			frm.set_value("set_target_warehouse", frappe.sys_defaults.default_warehouse || "");
		}
	},

	refresh(frm) {
		erpnext.stock.consignment_order.hide_unused_fields(frm);
		erpnext.stock.consignment_order.sync_target_warehouse(frm, false);
		erpnext.stock.consignment_order.set_print_hide(frm.doc);

		if (frm.fields_dict.items && frm.fields_dict.items.grid) {
			frm.fields_dict.items.grid.set_column_disp(["warehouse"], false);
			frm.fields_dict.items.grid.set_column_disp(["target_warehouse"], true);
		}
	},

	set_target_warehouse(frm) {
		erpnext.stock.consignment_order.sync_target_warehouse(frm, true);
	},

	company(frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
		if (frm.doc.company && frm.doc.tc_name == null) {
			frappe.db.get_value("Company", frm.doc.company, "default_selling_terms").then((r) => {
				if (r.message && r.message.default_selling_terms && !frm.doc.tc_name) {
					frm.set_value("tc_name", r.message.default_selling_terms);
				}
			});
		}
	}
});

frappe.ui.form.on("Delivery Note Item", {
	warehouse(frm, cdt, cdn) {
		if (frm.doctype !== "Consignment Order") return;
		frappe.model.set_value(cdt, cdn, "warehouse", "");
	},

	target_warehouse(frm, cdt, cdn) {
		if (frm.doctype !== "Consignment Order") return;
		frappe.model.set_value(cdt, cdn, "warehouse", "");
	},

	expense_account(frm, cdt, cdn) {
		if (frm.doctype !== "Consignment Order") return;
		const d = locals[cdt][cdn];
		frm.update_in_all_rows("items", "expense_account", d.expense_account);
	},

	cost_center(frm, cdt, cdn) {
		if (frm.doctype !== "Consignment Order") return;
		const d = locals[cdt][cdn];
		frm.update_in_all_rows("items", "cost_center", d.cost_center);
	}
});

erpnext.stock.consignment_order.sync_target_warehouse = function (frm, force_update) {
	if (!frm.doc.items || !frm.doc.set_target_warehouse) return;

	(frm.doc.items || []).forEach((row) => {
		if (force_update || !row.target_warehouse) {
			frappe.model.set_value(row.doctype, row.name, "target_warehouse", frm.doc.set_target_warehouse);
		}

		if (row.warehouse) {
			frappe.model.set_value(row.doctype, row.name, "warehouse", "");
		}
	});
};

erpnext.stock.consignment_order.hide_unused_fields = function (frm) {
	CO_HIDDEN_FIELDS.forEach((fieldname) => {
		if (frm.get_field(fieldname)) {
			frm.set_df_property(fieldname, "hidden", 1);
		}
	});
};

erpnext.stock.consignment_order.set_print_hide = function (doc) {
	const parent_map = frappe.meta.docfield_map[doc.doctype] || {};
	const item_map = frappe.meta.docfield_map["Delivery Note Item"] || {};

	if (!doc.print_without_amount) {
		if (parent_map.currency) parent_map.currency.print_hide = 0;
		if (parent_map.taxes) parent_map.taxes.print_hide = 0;
		if (item_map.rate) item_map.rate.print_hide = 0;
		if (item_map.discount_percentage) item_map.discount_percentage.print_hide = 0;
		if (item_map.price_list_rate) item_map.price_list_rate.print_hide = 0;
		if (item_map.amount) item_map.amount.print_hide = 0;
		if (item_map.discount_amount) item_map.discount_amount.print_hide = 0;
		return;
	}

	if (parent_map.currency) parent_map.currency.print_hide = 1;
	if (parent_map.taxes) parent_map.taxes.print_hide = 1;
	if (item_map.rate) item_map.rate.print_hide = 1;
	if (item_map.discount_percentage) item_map.discount_percentage.print_hide = 1;
	if (item_map.price_list_rate) item_map.price_list_rate.print_hide = 1;
	if (item_map.amount) item_map.amount.print_hide = 1;
	if (item_map.discount_amount) item_map.discount_amount.print_hide = 1;
};

delete erpnext.stock.delivery_note.set_print_hide;

function init_consignment_order_controller() {
	erpnext.stock.ConsignmentOrderController = class ConsignmentOrderController extends erpnext.stock.DeliveryNoteController {
		setup() {
			this.setup_posting_date_time_check();
			super.setup();

			this.frm.set_query("contact_person", erpnext.queries.contact_query);
			this.frm.set_query("customer_address", erpnext.queries.address_query);
			this.frm.set_query("shipping_address_name", erpnext.queries.address_query);
			this.frm.set_query("dispatch_address_name", erpnext.queries.dispatch_address_query);

			if (this.frm.fields_dict.tc_name) {
				this.frm.set_query("tc_name", function () {
					return { filters: { selling: 1 } };
				});
			}
		}

		onload() {
			super.onload();
		}

		refresh(doc, dt, dn) {
			super.refresh(doc, dt, dn);
			erpnext.stock.consignment_order.hide_unused_fields(this.frm);
			erpnext.stock.consignment_order.sync_target_warehouse(this.frm, false);
			erpnext.stock.consignment_order.set_print_hide(this.frm.doc);

			if (this.frm.fields_dict.items && this.frm.fields_dict.items.grid) {
				this.frm.fields_dict.items.grid.set_column_disp(["warehouse"], false);
				this.frm.fields_dict.items.grid.set_column_disp(["target_warehouse"], true);
			}
		}

		tc_name() {
			this.get_terms();
		}

		customer() {
			const me = this;
			erpnext.utils.get_party_details(this.frm, null, null, function () {
				me.apply_price_list();
			});
		}

		customer_address() {
			erpnext.utils.get_address_display(this.frm, "customer_address");
			erpnext.utils.set_taxes_from_address(
				this.frm,
				"customer_address",
				"customer_address",
				"shipping_address_name"
			);
		}

		shipping_address_name() {
			erpnext.utils.get_address_display(this.frm, "shipping_address_name", "shipping_address");
			erpnext.utils.set_taxes_from_address(
				this.frm,
				"shipping_address_name",
				"customer_address",
				"shipping_address_name"
			);
		}

		dispatch_address_name() {
			erpnext.utils.get_address_display(this.frm, "dispatch_address_name", "dispatch_address");
		}
	};

	extend_cscript(cur_frm.cscript, new erpnext.stock.ConsignmentOrderController({ frm: cur_frm }));
}

init_consignment_order_controller();

}