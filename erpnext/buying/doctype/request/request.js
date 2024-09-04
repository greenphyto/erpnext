// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/selling/sales_common.js' %}

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




	},
	refresh:function(frm){
		// if (frm.doc.docstatus == 1){
			// frm.add_custom_button(__('Sales Order'), ()=>{
			// 	frm.cscript.make_sales_order(frm);
			// }, __('Create'));
		// }

		frm.set_query("item_code", "items", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			var filters = {"is_stock_item": 1, "is_fixed_asset": 0}
			if (doc.non_package_item){
				filters['is_package_item']=0;
			}else{
				filters['is_package_item']=1;
			}
			return erpnext.queries.item(filters);
		})

		frm.cscript.change_package_display();

	},
	non_package_item: function(frm){
		frm.cscript.confirm_reset_item("non_package_item").then(r=>{
			if (r){
				frm.cscript.change_package_display();
				frm.cscript.calculate_rate();

			}
		});
	},
});

frappe.ui.form.on("Request Items", {
	item_code:function(doc, cdt, cdn){
		frappe.model.set_value(cdt,cdn,"packaging", "");
	}
})

function update_weight(frm) {
	frm.set_value("weight", flt(frm.doc.quantity * frm.doc.packaging_size));
}


erpnext.selling.RequestController = class RequestController extends erpnext.selling.SellingController {
	make_sales_order(frm){
		frappe.call({
			method:"erpnext.buying.doctype.request.request.create_sales_order",
			args:{
				request_name:frm.doc.name
			},
			callback:(r)=>{
				frappe.set_route("Form", "Sales Order", r.message);
			}
		})
	}

	change_package_display(){
		if (!this.frm.doc.non_package_item){
			this.frm.cscript.change_package_label(1);
		}else{
			this.frm.cscript.change_package_label(0);
		}
	}

	item_code(){
		// 
	}
	
	uom(doc,cdt,cdn){
		this.fetch_weight(cdt,cdn);
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
}

frappe.provide("cur_frm.cscript")
extend_cscript(cur_frm.cscript, new erpnext.selling.RequestController({frm: cur_frm}));
