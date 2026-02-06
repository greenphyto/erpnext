// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on("Consignment Request", {
	setup: function(frm) {

		frm.add_fetch('customer', 'tax_id', 'tax_id');

		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.stock_qty<=doc.delivered_qty) ? "green" : "orange" })

		frm.set_query('company_address', function(doc) {
			if(!doc.company) {
				frappe.throw(__('Please set Company'));
			}

			return {
				query: 'frappe.contacts.doctype.address.address.address_query',
				filters: {
					link_doctype: 'Company',
					link_name: doc.company
				}
			};
		})
	},
	refresh: function(frm) {
		frm.set_query("item_code", "items", function(doc, cdt, cdn) {
			var filters = {"is_fixed_asset": 0, "item_group": "Products"};
			if (!frm.doc.non_package_item){
				filters['is_package_item']=1;
				filters['is_stock_item']=1;
			}
			return erpnext.queries.item(filters);
		})
	},

	onload: function(frm) {
		if (!frm.doc.transaction_date){
			frm.set_value('transaction_date', frappe.datetime.get_today())
		}
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return {
				filters: [
					["Warehouse", "company", "in", ["", cstr(frm.doc.company)]],
				]
			};
		});

		frm.set_query('warehouse', 'items', function(doc, cdt, cdn) {
			let row  = locals[cdt][cdn];
			let query = {
				filters: [
					["Warehouse", "company", "in", ["", cstr(frm.doc.company)]],
				]
			};
			if (row.item_code) {
				query.query = "erpnext.controllers.queries.warehouse_query";
				query.filters.push(["Bin", "item_code", "=", row.item_code]);
			}
			return query;
		});
	},

	delivery_date: function(frm) {
		$.each(frm.doc.items || [], function(i, d) {
			if(!d.delivery_date) d.delivery_date = frm.doc.delivery_date;
		});
		refresh_field("items");
	}
});

frappe.ui.form.on("Consignment Request Item", {
	item_code: function(frm,cdt,cdn) {
		var row = locals[cdt][cdn];
		if (frm.doc.delivery_date) {
			row.delivery_date = frm.doc.delivery_date;
			refresh_field("delivery_date", cdn, "items");
		} else {
			frm.script_manager.copy_from_first_row("items", row, ["delivery_date"]);
		}
	},
	delivery_date: function(frm, cdt, cdn) {
		if(!frm.doc.delivery_date) {
			erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "delivery_date");
		}
	},
	uom: function(frm, cdt, cdn){
		fetch_package_weight(frm, cdt,cdn);
	}

});

function fetch_package_weight(frm,cdt,cdn){
	var d = locals[cdt][cdn];
	frappe.db.get_value("Packaging", d.uom, "total_weight").then(r=>{
		frappe.model.set_value(cdt,cdn, "weight_in_unit", r.message.total_weight);
	})
}

erpnext.selling.ConsignmentRequestController = class ConsignmentRequestController extends erpnext.selling.SellingController {
	onload(doc, dt, dn) {
		super.onload(doc, dt, dn);
	}

	refresh(doc, dt, dn) {
		var me = this;
		super.refresh();
		this.setup_button();
	}

	tc_name() {
		this.get_terms();
	}

		
	setup_button() {
		var me = this;
		if(this.frm.doc.docstatus==1) {
			this.frm.add_custom_button(__('Stock Transfer'), function() {
				me.make_stock_transfer();
			}, __('Create'));

			this.frm.add_custom_button(__('Stock Return'), function() {
				me.make_stock_return();
			}, __('Create'));

			this.frm.add_custom_button(__('Salvage Process'), function() {
				me.make_salvage_process();
			}, __('Create'));

			this.frm.add_custom_button(__('Delivery Note'), function() {
				me.make_delivery_note();
			}, __('Create'));
			
			this.frm.add_custom_button(__('Sales Invoice'), function() {
				me.make_sales_invoice();
			}, __('Create'));
		}
	}

	make_stock_transfer() {
		frappe.model.open_mapped_doc({
			method: "erpnext.gp_erp.doctype.consignment_request.consignment_request.make_stock_transfer",
			frm: this.frm,
		})
	}

	make_stock_return() {
		frappe.model.open_mapped_doc({
			method: "erpnext.gp_erp.doctype.consignment_request.consignment_request.make_stock_return",
			frm: this.frm,
		})
	}

	make_salvage_process() {
		frappe.model.open_mapped_doc({
			method: "erpnext.gp_erp.doctype.consignment_request.consignment_request.make_salvage_process",
			frm: this.frm
		})
	}


	make_delivery_note(delivery_dates) {
		frappe.model.open_mapped_doc({
			method: "erpnext.gp_erp.doctype.consignment_request.consignment_request.make_delivery_note",
			frm: this.frm,
			args: {
				delivery_dates
			}
		})
	}

	make_sales_invoice() {
		frappe.model.open_mapped_doc({
			method: "erpnext.gp_erp.doctype.consignment_request.consignment_request.make_sales_invoice",
			frm: this.frm
		})
	}

	hold_sales_order(){
		var me = this;
		var d = new frappe.ui.Dialog({
			title: __('Reason for Hold'),
			fields: [
				{
					"fieldname": "reason_for_hold",
					"fieldtype": "Text",
					"reqd": 1,
				}
			],
			primary_action: function() {
				var data = d.get_values();
				frappe.call({
					method: "frappe.desk.form.utils.add_comment",
					args: {
						reference_doctype: me.frm.doctype,
						reference_name: me.frm.docname,
						content: __('Reason for hold:') + ' ' + data.reason_for_hold,
						comment_email: frappe.session.user,
						comment_by: frappe.session.user_fullname
					},
					callback: function(r) {
						if(!r.exc) {
							me.update_status('Hold', 'On Hold')
							d.hide();
						}
					}
				});
			}
		});
		d.show();
	}
	close_sales_order(){
		var me = this;
		frappe.prompt(
			[{ fieldname: "reason", fieldtype: "Small Text", label: "Closing Reason", reqd: 1 }],
			function (val) {
				var reason = `<b>Closing reason:</b> ${val.reason}`;
				post_comment(reason);
			},
			"Consignment Request Closing",
			"Submit"
		);

		function post_comment(text){
			frappe
				.xcall("frappe.desk.form.utils.add_comment", {
					reference_doctype: me.frm.doctype,
					reference_name: me.frm.docname,
					content: text,
					comment_email: frappe.session.user,
					comment_by: frappe.session.user_fullname,
				})
				.then((comment) => {
					me.frm.cscript.update_status("Close", "Closed")
				})
		}
		
	}
	update_status(label, status){
		var doc = this.frm.doc;
		var me = this;
		frappe.ui.form.is_saving = true;
		frappe.call({
			method: "erpnext.selling.doctype.sales_order.sales_order.update_status",
			args: {status: status, name: doc.name},
			callback: function(r){
				me.frm.reload_doc();
			},
			always: function() {
				frappe.ui.form.is_saving = false;
			}
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.selling.ConsignmentRequestController({frm: cur_frm}));