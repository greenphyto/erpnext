// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'erpnext/selling/sales_common.js' %};

cur_frm.add_fetch('customer', 'tax_id', 'tax_id');

frappe.provide("erpnext.stock");
frappe.provide("erpnext.stock.delivery_note");
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Delivery Note", {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Packing Slip': 'Packing Slip',
			'Installation Note': 'Installation Note',
			'Sales Invoice': 'Sales Invoice',
			'Stock Entry': 'Return',
			'Shipment': 'Shipment'
		},
		frm.set_indicator_formatter('item_code',
			function(doc) {
				return (doc.docstatus==1 || doc.qty<=doc.actual_qty) ? "green" : "orange"
			})

		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});
		erpnext.queries.setup_warehouse_query(frm);

		frm.set_query('project', function(doc) {
			return {
				query: "erpnext.controllers.queries.get_project_name",
				filters: {
					'customer': doc.customer
				}
			}
		})

		frm.set_query('transporter', function() {
			return {
				filters: {
					'is_transporter': 1
				}
			}
		});

		frm.set_query('driver', function(doc) {
			return {
				filters: {
					'transporter': doc.transporter
				}
			}
		});


		frm.set_query('expense_account', 'items', function(doc, cdt, cdn) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						"report_type": "Profit and Loss",
						"company": doc.company,
						"is_group": 0
					}
				}
			}
		});

		frm.set_query('cost_center', 'items', function(doc, cdt, cdn) {
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				return {
					filters: {
						'company': doc.company,
						"is_group": 0
					}
				}
			}
		});

		frm.set_df_property('packed_items', 'cannot_add_rows', true);
		frm.set_df_property('packed_items', 'cannot_delete_rows', true);
	},

	is_donation: function(frm){
		frm.set_value("naming_series", 'DON-.YYYY.-.###');
		frappe.db.get_value("Company", frm.doc.company, ["donation_customer", "donation_account"]).then(r=>{
			frm.set_value("customer", r.message.donation_customer);
			set_donation_expense(frm, r.message.donation_account);
		});
	},
	
	is_giveaway: function(frm){
		frm.set_value("naming_series", 'GPO-.YYYY.-.###');
		frappe.db.get_value("Company", frm.doc.company, ["internal_staff_customer", "giveaway_account"]).then(r=>{
			frm.set_value("customer", r.message.internal_staff_customer)
			set_donation_expense(frm, r.message.giveaway_account);
		});
	},

	print_without_amount: function(frm) {
		erpnext.stock.delivery_note.set_print_hide(frm.doc);
	},

	refresh: function(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.is_return === 1 && frm.doc.per_billed !== 100) {
			frm.add_custom_button(__('Credit Note'), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
					frm: cur_frm,
				})
			}, __('Create'));
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if (frm.doc.docstatus == 1 && !frm.doc.inter_company_reference) {
			let internal = me.frm.doc.is_internal_customer;
			if (internal) {
				let button_label = (me.frm.doc.company === me.frm.doc.represents_company) ? "Internal Purchase Receipt" :
					"Inter Company Purchase Receipt";

				me.frm.add_custom_button(button_label, function() {
					frappe.model.open_mapped_doc({
						method: 'erpnext.stock.doctype.delivery_note.delivery_note.make_inter_company_purchase_receipt',
						frm: frm,
					});
				}, __('Create'));
			}
		}
		
		erpnext.add_image_slide(frm)
	},
	is_return: function(frm){
		frm.set_value("naming_series", "DO-RET-.YYYY.-.###")
	}
});

frappe.ui.form.on("Delivery Note Item", {
	expense_account: function(frm, dt, dn) {
		var d = locals[dt][dn];
		frm.update_in_all_rows('items', 'expense_account', d.expense_account);
	},
	cost_center: function(frm, dt, dn) {
		var d = locals[dt][dn];
		frm.update_in_all_rows('items', 'cost_center', d.cost_center);
	}
});

erpnext.stock.DeliveryNoteController = class DeliveryNoteController extends erpnext.selling.SellingController {
	setup(doc) {
		this.setup_posting_date_time_check();
		super.setup(doc);
		this.frm.make_methods = {
			'Delivery Trip': this.make_delivery_trip,
		};
	}
	refresh(doc, dt, dn) {
		var me = this;
		super.refresh();
		if ((!doc.is_return) && (doc.status!="Closed" || this.frm.is_new())) {
			if (this.frm.doc.docstatus===0) {
				this.frm.add_custom_button(__('Sales Order'),
					function() {
						if (!me.frm.doc.customer) {
							frappe.throw({
								title: __("Mandatory"),
								message: __("Please Select a Customer")
							});
						}
						erpnext.utils.map_current_doc({
							method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
							source_doctype: "Sales Order",
							target: me.frm,
							setters: {
								customer: me.frm.doc.customer,
							},
							get_query_filters: {
								docstatus: 1,
								status: ["not in", ["Closed", "On Hold"]],
								per_delivered: ["<", 99.99],
								company: me.frm.doc.company,
								project: me.frm.doc.project || undefined,
							}
						})
					}, __("Get Items From"));
			}
		}

		if (!doc.is_return && doc.status!="Closed") {
			if(doc.docstatus == 1) {
				this.frm.add_custom_button(__('Shipment'), function() {
					me.make_shipment() }, __('Create'));
			}

			if(flt(doc.per_installed, 2) < 100 && doc.docstatus==1)
				this.frm.add_custom_button(__('Installation Note'), function() {
					me.make_installation_note() }, __('Create'));

			if (doc.docstatus==1) {
				this.frm.add_custom_button(__('Sales Return'), function() {
					me.make_sales_return() }, __('Create'));
			}

			if (doc.docstatus==1) {
				this.frm.add_custom_button(__('Sales Replacement'), function() {
					me.make_sales_replacement() }, __('Create'));
			}

			// if (doc.docstatus==1) {
			// 	this.frm.add_custom_button(__('Delivery Trip'), function() {
			// 		me.make_delivery_trip() }, __('Create'));
			// }

			if(doc.docstatus==0 && !doc.__islocal) {
				this.frm.add_custom_button(__('Packing Slip'), function() {
					frappe.model.open_mapped_doc({
						method: "erpnext.stock.doctype.delivery_note.delivery_note.make_packing_slip",
						frm: me.frm
					}) }, __('Create'));
			}

			if (!doc.__islocal && doc.docstatus==1) {
				this.frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}

		if (doc.docstatus > 0) {
			this.show_stock_ledger();
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				this.show_general_ledger();
			}
			if (this.frm.has_perm("submit") && doc.status !== "Closed") {
				me.frm.add_custom_button(__("Close"), function() { me.close_delivery_note() },
					__("Status"))
			}
		}

		if(doc.docstatus==1 && !doc.is_return && doc.status!="Closed" && flt(doc.per_billed) < 100) {
			// show Make Invoice button only if Delivery Note is not created from Sales Invoice
			var from_sales_invoice = false;
			from_sales_invoice = me.frm.doc.items.some(function(item) {
				return item.against_sales_invoice ? true : false;
			});

			if(!from_sales_invoice) {
				this.frm.add_custom_button(__('Sales Invoice'), function() { me.make_sales_invoice() },
					__('Create'));
			}
		}

		if(doc.docstatus==1 && doc.status === "Closed" && this.frm.has_perm("submit")) {
			this.frm.add_custom_button(__('Reopen'), function() { me.reopen_delivery_note() },
				__("Status"))
		}
		erpnext.stock.delivery_note.set_print_hide(doc, dt, dn);

		if(doc.docstatus==1 && !doc.is_return && !doc.auto_repeat) {
			cur_frm.add_custom_button(__('Subscription'), function() {
				erpnext.utils.make_subscription(doc.doctype, doc.name)
			}, __('Create'))
		}
		me.frm.cscript.change_package_display();
	}

	non_package_item(){
		var me = this;
		me.frm.cscript.confirm_reset_item("non_package_item").then(r=>{
			if (r){
				me.frm.cscript.change_package_display();
			}
		});
	}

	change_package_display(){
		if (!this.frm.doc.non_package_item){
			this.frm.cscript.change_package_label(1);
		}else{
			this.frm.cscript.change_package_label(0);
		}
	}

	make_shipment() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.delivery_note.delivery_note.make_shipment",
			frm: this.frm
		})
	}

	make_sales_invoice() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
			frm: this.frm
		})
	}

	make_installation_note() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.delivery_note.delivery_note.make_installation_note",
			frm: this.frm
		});
	}

	make_sales_return() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_return",
			frm: this.frm
		})
	}

	make_sales_replacement() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_replacement",
			frm: this.frm
		})
	}

	make_delivery_trip() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.delivery_note.delivery_note.make_delivery_trip",
			frm: cur_frm
		})
	}

	tc_name() {
		this.get_terms();
	}

	items_on_form_rendered(doc, grid_row) {
		erpnext.setup_serial_or_batch_no();
	}

	packed_items_on_form_rendered(doc, grid_row) {
		erpnext.setup_serial_or_batch_no();
	}

	close_delivery_note(doc){
		this.update_status("Closed")
	}

	reopen_delivery_note() {
		this.update_status("Submitted")
	}

	update_status(status) {
		var me = this;
		frappe.ui.form.is_saving = true;
		frappe.call({
			method:"erpnext.stock.doctype.delivery_note.delivery_note.update_delivery_note_status",
			args: {docname: me.frm.doc.name, status: status},
			callback: function(r){
				if(!r.exc)
					me.frm.reload_doc();
			},
			always: function(){
				frappe.ui.form.is_saving = false;
			}
		})
	}
};

extend_cscript(cur_frm.cscript, new erpnext.stock.DeliveryNoteController({frm: cur_frm}));

frappe.ui.form.on('Delivery Note', {
	setup: function(frm) {
		if(frm.doc.company) {
			frm.trigger("unhide_account_head");
		}
	},

	company: function(frm) {
		frm.trigger("unhide_account_head");
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	unhide_account_head: function(frm) {
		// unhide expense_account and cost_center if perpetual inventory is enabled in the company
		var aii_enabled = erpnext.is_perpetual_inventory_enabled(frm.doc.company)
		frm.fields_dict["items"].grid.set_column_disp(["expense_account", "cost_center"], aii_enabled);
	}
})


erpnext.stock.delivery_note.set_print_hide = function(doc, cdt, cdn){
	var dn_fields = frappe.meta.docfield_map['Delivery Note'];
	var dn_item_fields = frappe.meta.docfield_map['Delivery Note Item'];
	var dn_fields_copy = dn_fields;
	var dn_item_fields_copy = dn_item_fields;
	if (doc.print_without_amount) {
		dn_fields['currency'].print_hide = 1;
		dn_item_fields['rate'].print_hide = 1;
		dn_item_fields['discount_percentage'].print_hide = 1;
		dn_item_fields['price_list_rate'].print_hide = 1;
		dn_item_fields['amount'].print_hide = 1;
		dn_item_fields['discount_amount'].print_hide = 1;
		dn_fields['taxes'].print_hide = 1;
	} else {
		if (dn_fields_copy['currency'].print_hide != 1)
			dn_fields['currency'].print_hide = 0;
		if (dn_item_fields_copy['rate'].print_hide != 1)
			dn_item_fields['rate'].print_hide = 0;
		if (dn_item_fields_copy['amount'].print_hide != 1)
			dn_item_fields['amount'].print_hide = 0;
		if (dn_item_fields_copy['discount_amount'].print_hide != 1)
			dn_item_fields['discount_amount'].print_hide = 0;
		if (dn_fields_copy['taxes'].print_hide != 1)
			dn_fields['taxes'].print_hide = 0;
	}
}


frappe.tour['Delivery Note'] = [
	{
		fieldname: "customer",
		title: __("Customer"),
		description: __("This field is used to set the 'Customer'.")
	},
	{
		fieldname: "items",
		title: __("Items"),
		description: __("This table is used to set details about the 'Item', 'Qty', 'Basic Rate', etc.") + " " +
		__("Different 'Source Warehouse' and 'Target Warehouse' can be set for each row.")
	},
	{
		fieldname: "set_posting_time",
		title: __("Edit Posting Date and Time"),
		description: __("This option can be checked to edit the 'Posting Date' and 'Posting Time' fields.")
	}
]

cur_frm.cscript['set_cost_center'] = function(frm, cdt, cdn, field_account="expense_account"){
	var d = locals[cdt][cdn];
	return new Promise((resolve)=>{
		if (d[field_account]){
			erpnext.utils.get_cost_center(d[field_account], frm.doc.company).then(r=>{
				frappe.model.set_value(cdt,cdn,"cost_center", r.value);
			})
		}else{
			frappe.model.set_value(cdt,cdn,"cost_center", "");
			resolve()
		}
	})
}

frappe.ui.form.on("Delivery Note Item", {
	expense_account: function(frm,cdt,cdn){
		frm.cscript.set_cost_center(frm, cdt,cdn);
	}
})

frappe.ui.form.on("Sales Taxes and Charges", {
	account_head: function(frm,cdt,cdn){
		frm.cscript.set_cost_center(frm, cdt,cdn,"account_head");
	}
})

function set_donation_expense(frm, account){
	$.each(frm.doc.items, (i, r)=>{
		frappe.model.set_value(r.doctype, r.name, "expense_account", account);
	});
	frm.refresh_field("items");
}

erpnext.add_image_slide = function(frm){
	var content = $(`
	<div id="splide" class="splide">
        <div class="splide__track">
            <ul class="splide__list">
            </ul>
        </div>
    </div>
	<div class="custom-arrows">
        <button id="prev-slide">&#9665;</button>
        <button id="next-slide">&#9655;</button>
    </div>
	`)

	if (is_null(frm.doc.attachment)){
		return
	}

	$.each(frm.doc.attachment.split(";"), (i, v)=>{
		content.find(".splide__list").append(`
			<li class="splide__slide">
				<img src="${v}">
			</li>
		`)
	})

	var wrapper = frm.fields_dict.attachment_preview.$wrapper;
	wrapper.empty();
	wrapper.append(content);
	frm.slide_image = new erpnext.splide('#splide', {
		type: 'loop',
		autoplay: true,
		interval: 3000,
		perPage: 1,
		arrows: false
	}).mount();

	document.getElementById('prev-slide').addEventListener('click', function() {
		frm.slide_image.go('<');
	});
	
	document.getElementById('next-slide').addEventListener('click', function() {
		frm.slide_image.go('>');
	});
}