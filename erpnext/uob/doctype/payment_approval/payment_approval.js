// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Approval', {
	refresh: function(frm) {
		// Add button similar to "Get Items From" in Sales Invoice
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Get Invoice'), () => {
				frm.cscript.get_unpaid_purchase_invoices();
			});
		}
		frm.set_query("invoice_no", "invoices", (doc, cdt, cdn)=>{
			return{
				filters:{
					docstatus:1,
					outstanding_amount:[">", 0],
					currency:doc.currency
				}
			}
		})

		frm.set_query("supplier_bank_no", "invoices", (doc, cdt, cdn)=>{
			var d = locals[cdt][cdn]
			return{
				filters:{
					party: d.party,
					party_type:"Supplier",
					currency:doc.currency
				}
			}
		})

		frm.set_query("bank_account", (doc, cdt, cdn)=>{
			var currency = doc.currency;
			if (!currency){
				frappe.throw("Please set currency.")
			}
			return{
				filters:{
					"currency":currency
				}
			}
		})

		if(!frm.doc.requested_by && frm.is_dirty()){
			frm.set_value("requested_by", frappe.session.user)
		}
		frm.cscript.setup_method();
	},
	payment_method: function(frm){
		frm.cscript.setup_method();
	},
	payment_type: function(frm){
		frm.cscript.setup_method();
	},
	before_workflow_action: function(frm){
		return new Promise((resolve, reject) => {
			frm.cscript.reject_payment_approval().then((r)=>{
				if (r){
					resolve()
				}
			});
		})
	},
	currency: function(frm){
		frm.set_value("bank_account", "");
		frm.set_value("invoices", [])
	}
})

$.extend(cur_frm.cscript, {
	get_unpaid_purchase_invoices(){
		var me = this;
			const mapping_dialog = erpnext.utils.map_current_doc({
				method: "erpnext.uob.doctype.payment_approval.payment_approval.make_payment_approval",
				source_doctype: "Purchase Invoice",
				target: me.frm,
				date_field: "posting_date",
				setters: [
					{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: me.frm.doc.company },
					{ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier" },
					{ fieldname: "posting_date", label: __("Posting Date"), fieldtype: "Date", default: "" },
					{ fieldname: "days_ago", label: __("Days Old"), fieldtype: "Int", read_only: 0 },
					{ fieldname: "outstanding_amount", label: __("Outstanding Amount"), fieldtype: "Currency" }
				],
				get_query_method:"erpnext.uob.doctype.payment_approval.payment_approval.search_purchase_invoice",
				get_query_filters: {
					docstatus: 1,
					company: me.frm.doc.company,
					outstanding_amount: [">", 0]
				},
				size: 'extra-large'
			});
	},
	setup_method(){
		var me = this.frm;
		var doc = this.frm.doc;
		var payment_method_field = me.fields_dict.payment_method;
		var payment_property_field = me.fields_dict.payment_property;
		var cheque_type_field = me.fields_dict.cheque_method;
		if (doc.payment_type=="Transfer" && in_list(["IBG", "FAST"], doc.payment_method)){
			payment_property_field.df.hidden = 1
			payment_method_field.df.hidden = 0
		} else if (doc.payment_type=="Cheque"){
			payment_property_field.df.options = "CHQ\nCO"
			payment_property_field.df.hidden = 0
			payment_method_field.df.hidden = 1
		} else{
			payment_property_field.df.options = ""
			payment_property_field.df.hidden = 1
			payment_method_field.df.hidden = 0
		}
		cheque_type_field.df.options = [
			{label:"MLCD - Mail to Creditor (Beneficiary)", value:"MLCD"},
			{label:"MLFA - Mail to Final Agent (Debtor or Agent)", value:"MLFA"},
			{label:"PUDB - Pick up by Debtor (Payer)", value:"PUDB"},
		]
		cheque_type_field.refresh()
		payment_property_field.refresh()
		payment_method_field.refresh()
	},
	reject_payment_approval(){
		return new Promise((resolve) => {
			var me = this;
			if (me.frm.selected_workflow_action == "Reject"){
				var d = new frappe.ui.Dialog({
					title: __('Reason for Reject'),
					fields: [
						{
							"fieldname": "reason",
							"fieldtype": "Small Text",
							"label": "Reason:",
							"reqd": 1,
						}
					],
					primary_action: function() {
						var data = d.get_values();
						let reason = 'Reason for Reject: ' + data.reason;
		
						frappe.call({
							method: "frappe.desk.form.utils.add_comment",
							args: {
								reference_doctype: me.frm.doctype,
								reference_name: me.frm.docname,
								content: __(reason),
								comment_email: frappe.session.user,
								comment_by: frappe.session.user_fullname
							},
							callback: function(r) {
								me.frm.reload_doc()
								d.finish = true;
								d.hide();
							}
						});
					},
					onhide:()=>{
						if (d.finish){
							resolve(true);
						}else{
							resolve(false);
						}
					}
				});
				d.show();
			}else{
				resolve(true);
			}
		})
	}
})

// Extend with summary renderer without touching existing cscript methods
$.extend(cur_frm.cscript, {
	render_summary(frm){
		try {
			const fld = frm.fields_dict && frm.fields_dict.summary_wrapper;
			if (!fld || !fld.$wrapper) return;
			const items = (frm.doc.invoices || []).filter(r => r && r.party);
			if (!items.length) {
				fld.$wrapper.html('<div class="text-muted">No invoices to summarize.</div>');
				return;
			}

			const groups = {};
			let grand = 0;
			items.forEach(r => {
				const key = r.party;
				const amt = parseFloat(r.amount) || 0;
				grand += amt;
				if (!groups[key]) groups[key] = { supplier: key, count: 0, total: 0 };
				groups[key].count += 1;
				groups[key].total += amt;
			});

			const currency = frm.doc.currency || null;
			const fmt = (v) => frappe.format(v, { fieldtype: 'Currency', options: currency });
			const body = Object.values(groups)
				.sort((a,b) => a.supplier.localeCompare(b.supplier))
				.map(it => `
					<tr>
						<td>${frappe.utils.escape_html(it.supplier)}</td>
						<td class="text-right">${it.count}</td>
						<td class="text-right">${fmt(it.total)}</td>
					</tr>
				`).join('');

			const html = `
				<div class="mt-3">
					<table class="table table-sm table-bordered" style="margin:auto; width: 90%;">
						<thead class="thead-light">
							<tr>
								<th>Supplier</th>
								<th class="text-right">Invoices</th>
								<th class="text-right">Total Amount</th>
							</tr>
						</thead>
						<tbody>${body}</tbody>
						<tfoot>
							<tr>
								<th>Total</th>
								<th class="text-right">${items.length}</th>
								<th class="text-right">${fmt(grand)}</th>
							</tr>
						</tfoot>
					</table>
				</div>`;

			fld.$wrapper.html(html);
		} catch (e) {
			if (console && console.warn) console.warn('Summary render failed', e);
		}
	}
});

// Ensure summary renders on refresh and currency changes
frappe.ui.form.on('Payment Approval', {
	refresh(frm) {
		if (frm.cscript.render_summary) frm.cscript.render_summary(frm);
	},
	currency(frm) {
		setTimeout(() => {
			if (frm.cscript.render_summary) frm.cscript.render_summary(frm);
		}, 0);
	},
	invoices_add(frm) {
		if (frm.cscript.render_summary) frm.cscript.render_summary(frm);
	},
	invoices_remove(frm) {
		if (frm.cscript.render_summary) frm.cscript.render_summary(frm);
	}
});

// Child table field events to keep summary in sync real-time
frappe.ui.form.on('Payment Invoice List', {
	invoice_no(frm) { if (frm.cscript.render_summary) frm.cscript.render_summary(frm); },
	party(frm) { if (frm.cscript.render_summary) frm.cscript.render_summary(frm); },
	amount(frm) { if (frm.cscript.render_summary) frm.cscript.render_summary(frm); },
	currency(frm) { if (frm.cscript.render_summary) frm.cscript.render_summary(frm); }
});
