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


		frm.set_query("packaging", "items", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			if (!row.item_code){
				frappe.throw(__("Select item first"))
			}
			return {
				filters: {
					"item": row.item_code
				},
				query:"erpnext.selling.doctype.sales_order.sales_order.get_packaging_available"
			}
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
		if (frm.doc.docstatus == 1){
			frm.add_custom_button(__('Sales Order'), ()=>{
				frm.cscript.make_sales_order(frm);
			}, __('Create'));
		}
	},
	non_package_item: function(frm){
		frm.cscript.confirm_reset_item("non_package_item").then(r=>{
			if (r){
				frm.cscript.change_package_display();
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
}

frappe.provide("cur_frm.cscript")
extend_cscript(cur_frm.cscript, new erpnext.selling.RequestController({frm: cur_frm}));
