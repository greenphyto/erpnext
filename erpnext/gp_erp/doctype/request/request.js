// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

erpnext.sales_common.setup_selling_controller();

frappe.ui.form.on("Request", {
	quantity: function (frm) {
		update_weight(frm);
	},
	packaging_size: function (frm) {
		update_weight(frm);
	},
	setup: function (frm) {
		frm.set_query("department", (doc)=>{
			return {
				filters:{
					is_group:0
				}
			}
		})

		frm.set_query("item_code", "items", function(doc, cdt, cdn) {
			return {
				filters: {
					item_group: "Products"
				}
			}
		});

		frm.set_query("uom", "items", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			if (!row.item_code) frappe.throw(__("Please select Item"));
			var args =  erpnext.queries.uom({
				"parent": row.item_code,
				"is_packaging": doc.non_package_item? 0 : 1
			})

			return args;
		});

		frm.set_query("type_of_vegetable", (doc)=>{
			return {
				filters:{
					item_group:"Products",
					disabled:0
				}
			}
		})

		frm.set_query("packaging_item", "items", function(doc, cdt, cdn) {
			return {
				filters: {
					material_group: "Other Packaging"
				}
			}
		});




	},
	refresh:function(frm){
		// if (frm.doc.docstatus == 1){
			// frm.add_custom_button(__('Sales Order'), ()=>{
			// 	frm.cscript.make_sales_order(frm);
			// }, __('Create'));
		// }

		frm.set_query("item_code", "items", function(doc, cdt, cdn) {
			var filters = {"is_stock_item": 1, "is_fixed_asset": 0, "item_group": "Products"}
			if (!doc.non_package_item){
				filters['is_package_item']=1;
			}
			return erpnext.queries.item(filters);
		})

		// if (frm.doc.docstatus==1){
		// 	frm.add_custom_button(__('Update Items'), () => {
		// 		erpnext.utils.update_child_items_request({
		// 			frm: frm,
		// 			child_docname: "items",
		// 			child_doctype: "Request Items",
		// 			cannot_add_row: false
		// 		})
		// 	});
		// }

		frm.cscript.add_button_make_salad(frm.doc);

		// Render tray data on load
		if (frm.doc.tray_data_html) {
			frm.get_field("tray_data_html").$wrapper.html(frm.doc.tray_data_html);
		}

	},

	posting_date:function(frm){
		frm.cscript.calculate_duration_days();
	},
	delivery_date:function(frm){
		frm.cscript.calculate_duration_days();
	}

});

frappe.ui.form.on("Request", {
	get_tray_data: function(frm) {
		var item_codes = [];
		$.each(frm.doc.items || [], function(i, d) {
			if (d.item_code) {
				item_codes.push(d.item_code);
			}
		});

		if (!item_codes.length) {
			frappe.msgprint(__("Please add items first"));
			return;
		}

		frappe.dom.freeze(__("Fetching tray data..."));

		frappe.call({
			method: "erpnext.gp_erp.doctype.request.request.fetch_tray_data",
			args: {
				item_codes: item_codes
			},
			callback: function(r) {
				frappe.dom.unfreeze();
				if (r.message) {
					frappe.call({
						method: "erpnext.gp_erp.doctype.request.request.generate_tray_data_html",
						args: {
							tray_data_list: r.message
						},
						callback: function(r) {
							if (r.message) {
								frm.get_field("tray_data_html").$wrapper.html(r.message);
							}
						}
					});
				}
			},
			error: function(r) {
				frappe.dom.unfreeze();
				frappe.msgprint(__("Error fetching tray data"));
			}
		});
	}
});

frappe.ui.form.on("Request Items", {
	item_code:function(doc, cdt, cdn){
		frappe.model.set_value(cdt,cdn,"packaging", "");

		// Auto-refresh tray data
		var item_codes = [];
		$.each(cur_frm.doc.items || [], function(i, d) {
			if (d.item_code) {
				item_codes.push(d.item_code);
			}
		});

		if (item_codes.length) {
			frappe.call({
				method: "erpnext.gp_erp.doctype.request.request.fetch_tray_data",
				args: {
					item_codes: item_codes
				},
				callback: function(r) {
					if (r.message) {
						frappe.call({
							method: "erpnext.gp_erp.doctype.request.request.generate_tray_data_html",
							args: {
								tray_data_list: r.message
							},
							callback: function(r) {
								if (r.message) {
									cur_frm.get_field("tray_data_html").$wrapper.html(r.message);
								}
							}
						});
					}
				}
			});
		}
	}
})

function update_weight(frm) {
	frm.set_value("weight", flt(frm.doc.quantity * frm.doc.packaging_size));
}


erpnext.selling.RequestController = class RequestController extends erpnext.selling.SellingController {
	make_sales_order(frm){
		frappe.call({
			method:"erpnext.gp_erp.doctype.request.request.create_sales_order",
			args:{
				request_name:frm.doc.name
			},
			callback:(r)=>{
				frappe.set_route("Form", "Sales Order", r.message);
			}
		})
	}

	calculate_duration_days(){
		if (this.frm.doc.delivery_date && this.frm.doc.posting_date){
			let duration_days = frappe.datetime.get_day_diff(this.frm.doc.delivery_date, this.frm.doc.posting_date);
			this.frm.set_value("duration_days", duration_days);
		}
	}

	item_code(doc,cdt,cdn){
		this.add_uom_default(doc,cdt,cdn)
		this.frm.cscript.get_carton_detail(doc, cdt, cdn);
	}
	
	uom(doc,cdt,cdn){
		this.fetch_weight(cdt,cdn);
		this.frm.cscript.get_carton_detail(doc, cdt, cdn);
	}

	fetch_weight(cdt,cdn){
		var d = locals[cdt][cdn];
		if (!this.frm.doc.non_package_item){
			frappe.db.get_value("Packaging", d.uom, "total_weight").then(r=>{
				frappe.model.set_value(cdt,cdn, "unit_weight", r.message.total_weight);

			});
		}else{
			if (in_list(['Kg', 'Litre'], d.uom)){
				frappe.model.set_value(cdt,cdn, "unit_weight", d.qty);
			}
		}
	}

	qty(){
		this.calculate_rate();
	}

	unit_weight(){
		this.calculate_rate();
	}

	validate(){
		
	}

	rate(){
		this.calculate_rate();
	}

	calculate_rate(){
		var total_price = 0;
		var total_weight = 0;
		$.each(this.frm.doc.items, (i, d)=>{
			console.log(i, d);
			var amount = d.rate * flt(d.qty);
			total_price += amount;
			total_weight += d.unit_weight;
			frappe.model.set_value(d.doctype, d.name, "amount", amount);
		})
		this.frm.set_value("total_price", total_price);
		this.frm.set_value("total_weight", total_weight);
	}

	add_uom_default(doc, cdt, cdn){
		if (doc.non_package_item){
			frappe.model.set_value(cdt,cdn, "uom", "Kg")
		}
	}

	add_button_make_salad(doc, cdt, cdn){
		var me = this;
		if (doc.items.some(row => row.is_salad_product && !row.stock_entry && cint(row.progress) == 100 )){
			me.frm.add_custom_button(__('Make Salad'), function () {
				frappe.call({
					method:"erpnext.controllers.foms.manually_create_salad",
					args:{
						doctype:"Request",
						name:doc.name
					},
					callback:(r)=>{
						me.frm.reload_doc();
						frappe.msgprint(r.message);
					}
				})
			});
		}
	}
}

frappe.provide("cur_frm.cscript")
extend_cscript(cur_frm.cscript, new erpnext.selling.RequestController({frm: cur_frm}));

erpnext.utils.update_child_items_request = function(opts) {
	const frm = opts.frm;
	const cannot_add_row = 1;
	const child_docname = 'items';
	const child_meta = `Request Item`;

	var item_query = function() {
		let filters;
		filters = {"is_sales_item": 1};
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: filters
		};
	}

	if (opts.item_query){
		item_query = opts.item_query;
	}

	this.data = [];
	const fields = [{
		fieldtype:'Data',
		fieldname:"docname",
		read_only: 1,
		hidden: 1,
	}, {
		fieldtype:'Link',
		fieldname:"item_code",
		options: 'Item',
		in_list_view: 1,
		read_only: 1,
		disabled: 0,
		label: __('Item Code'),
	}, {
		fieldtype:'Link',
		fieldname:'uom',
		options: 'UOM',
		read_only: 1,
		label: __('UOM'),
		in_list_view: 1,
		reqd: 1,
	}, {
		fieldtype:'Float',
		fieldname:"qty",
		default: 0,
		read_only: 0,
		in_list_view: 1,
		label: __('Qty'),
		precision: 5
	}]

	const dialog = new frappe.ui.Dialog({
		title: __("Update Items"),
		fields: [
			{
				fieldname: "trans_items",
				fieldtype: "Table",
				label: "Items",
				cannot_add_rows: cannot_add_row,
				in_place_edit: false,
				reqd: 1,
				data: this.data,
				get_data: () => {
					return this.data;
				},
				fields: fields
			},
		],
		primary_action: function() {
			const trans_items = this.get_values()["trans_items"].filter((item) => !!item.item_code);
			frappe.call({
				method: 'erpnext.gp_erp.doctype.request.request.update_request',
				freeze: true,
				args: {
					request_no: frm.doc.name, 
					items: trans_items, 
					delivery_date: ''
				},
				callback: function() {
					frm.reload_doc();
				}
			});
			this.hide();
			refresh_field("items");
		},
		size:"large",
		primary_action_label: __('Update')
	});

	frm.doc[opts.child_docname].forEach(d => {
		dialog.fields_dict.trans_items.df.data.push({
			"docname": d.name,
			"name": d.name,
			"item_code": d.item_code,
			"delivery_date": d.delivery_date,
			"schedule_date": d.schedule_date,
			"conversion_factor": d.conversion_factor,
			"qty": d.qty,
			"rate": d.rate,
			"uom": d.uom
		});
		this.data = dialog.fields_dict.trans_items.df.data;
		dialog.fields_dict.trans_items.grid.refresh();
	})
	dialog.show();
}