// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Supplier", {
	setup: function (frm) {
		frm.set_query('default_price_list', { 'buying': 1 });
		if (frm.doc.__islocal == 1) {
			frm.set_value("represents_company", "");
		}
		frm.set_query('account', 'accounts', function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					'account_type': 'Payable',
					'company': d.company,
					"is_group": 0
				}
			}
		});
		frm.set_query("default_bank_account", function() {
			return {
				filters: {
					"is_company_account":1
				}
			}
		});

		frm.set_query("default_bank_account_no", function(doc) {
			return {
				filters: {
					"party":doc.name,
					"party_type":"Supplier"
				}
			}
		});

		frm.set_query("supplier_primary_contact", function(doc) {
			return {
				query: "erpnext.buying.doctype.supplier.supplier.get_supplier_primary_contact",
				filters: {
					"supplier": doc.name
				}
			};
		});

		frm.set_query("supplier_primary_address", function(doc) {
			return {
				filters: {
					"link_doctype": "Supplier",
					"link_name": doc.name
				}
			};
		});

		frm.set_query("item_code", "item_supplier", function(doc) {
			return {
				filters: {
					"disabled": 0,
					"is_purchase_item": 1
				}
			};
		});
	},

	refresh: function (frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Supplier' }

		if (frappe.defaults.get_default("supp_master_name") != "Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		if (frm.doc.__islocal) {
			hide_field(['address_html','contact_html']);
			frappe.contacts.clear_address_and_contact(frm);
		}
		else {
			unhide_field(['address_html','contact_html']);
			frappe.contacts.render_address_and_contact(frm);

			// custom buttons
			frm.add_custom_button(__('Accounting Ledger'), function () {
				frappe.set_route('query-report', 'General Ledger',
					{ party_type: 'Supplier', party: frm.doc.name });
			}, __("View"));

			frm.add_custom_button(__('Accounts Payable'), function () {
				frappe.set_route('query-report', 'Accounts Payable', { supplier: frm.doc.name });
			}, __("View"));

			frm.add_custom_button(__('Bank Account'), function () {
				erpnext.utils.make_bank_account(frm.doc.doctype, frm.doc.name);
			}, __('Create'));

			frm.add_custom_button(__('Pricing Rule'), function () {
				erpnext.utils.make_pricing_rule(frm.doc.doctype, frm.doc.name);
			}, __('Create'));

			frm.add_custom_button(__('Get Supplier Group Details'), function () {
				frm.trigger("get_supplier_group_details");
			}, __('Actions'));

			if (cint(frappe.defaults.get_default("enable_common_party_accounting"))) {
				frm.add_custom_button(__('Link with Customer'), function () {
					frm.trigger('show_party_link_dialog');
				}, __('Actions'));
			}

			// indicators
			erpnext.utils.set_party_dashboard_indicators(frm);
		}

		frm.set_df_property("supplier_code_series", "options", [
			{"label":"S0.#### (AP Trade Creditors)", "value":"S0.####"},
			{"label":"S1.#### (Other Creditors)", "value":"S1.####"},
			{"label":"S2.#### (Bank Accounts)", "value":"S2.####"},
			{"label":"S3.#### (Hire Purchase)", "value":"S3.####"},
		])
	},
	supplier_code_series: function(frm){
		frappe.call({
			method: "erpnext.buying.doctype.supplier.supplier.get_exists_series",
			args:{
				"series": frm.doc.supplier_code_series,
				"doctype": frm.doc.doctype,
				"name": frm.doc.name,
				"field_series": "supplier_code_series", 
				"field_code": "supplier_code", 
			},
			callback: function(r) {
				frm.set_value("supplier_code", r.message)
			}
		});
	},
	get_supplier_group_details: function(frm) {
		frappe.call({
			method: "get_supplier_group_details",
			doc: frm.doc,
			callback: function() {
				frm.refresh();
			}
		});
	},

	supplier_primary_address: function(frm) {
		if (frm.doc.supplier_primary_address) {
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: {
					"address_dict": frm.doc.supplier_primary_address
				},
				callback: function(r) {
					frm.set_value("primary_address", r.message);
				}
			});
		}
		if (!frm.doc.supplier_primary_address) {
			frm.set_value("primary_address", "");
		}
	},

	supplier_primary_contact: function(frm) {
		if (!frm.doc.supplier_primary_contact) {
			frm.set_value("mobile_no", "");
			frm.set_value("email_id", "");
		}
	},

	is_internal_supplier: function(frm) {
		if (frm.doc.is_internal_supplier == 1) {
			frm.toggle_reqd("represents_company", true);
		}
		else {
			frm.toggle_reqd("represents_company", false);
		}
	},
	show_party_link_dialog: function(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __('Select a Customer'),
			fields: [{
				fieldtype: 'Link', label: __('Customer'),
				options: 'Customer', fieldname: 'customer', reqd: 1
			}],
			primary_action: function({ customer }) {
				frappe.call({
					method: 'erpnext.accounts.doctype.party_link.party_link.create_party_link',
					args: {
						primary_role: 'Supplier',
						primary_party: frm.doc.name,
						secondary_party: customer
					},
					freeze: true,
					callback: function() {
						dialog.hide();
						frappe.msgprint({
							message: __('Successfully linked to Customer'),
							alert: true
						});
					},
					error: function() {
						dialog.hide();
						frappe.msgprint({
							message: __('Linking to Customer Failed. Please try again.'),
							title: __('Linking Failed'),
							indicator: 'red'
						});
					}
				});
			},
			primary_action_label: __('Create Link')
		});
		dialog.show();
	}
});


frappe.provide("frappe.contacts");

$.extend(frappe.contacts, {
	clear_address_and_contact: function (frm) {
		$(frm.fields_dict["address_html"].wrapper).html("");
		frm.fields_dict["contact_html"] && $(frm.fields_dict["contact_html"].wrapper).html("");
		frm.fields_dict["bank_list_html"] && $(frm.fields_dict["bank_list_html"].wrapper).html("");
	},

	render_address_and_contact: function (frm) {
		// render address
		if (frm.fields_dict["address_html"] && "addr_list" in frm.doc.__onload) {
			$(frm.fields_dict["address_html"].wrapper)
				.html(frappe.render_template("address_list", frm.doc.__onload))
				.find(".btn-address")
				.on("click", function () {
					frappe.new_doc("Address");
				});
		}

		// render contact
		if (frm.fields_dict["contact_html"] && "contact_list" in frm.doc.__onload) {
			$(frm.fields_dict["contact_html"].wrapper)
				.html(frappe.render_template("contact_list", frm.doc.__onload))
				.find(".btn-contact")
				.on("click", function () {
					frappe.new_doc("Contact");
				});
		}

		// render bank accounts
		if (frm.fields_dict["bank_list_html"] && "bank_account_list" in frm.doc.__onload) {
			$(frm.fields_dict["bank_list_html"].wrapper)
				.html( frappe.render_template(frappe.contacts.bank_account_list_template, frm.doc.__onload))
				.find(".btn-bank-account")
				.on("click", function () {
					frappe.new_doc("Bank Number", {
						party_type: frm.doctype,
						party: frm.doc.name
					});
				});

			// Set default bank if available
			let default_bank = frm.doc.__onload.bank_account_list.find(x => x.is_default);
			if (default_bank && default_bank.bank_number) {
				frm.set_value("default_bank_account_no", default_bank.bank_number);
			}
		}
	},

	bank_account_list_template: `
		<div class="row">
		{% for (var i = 0, l = bank_account_list.length; i < l; i++) { %}
			<div class="col-sm-6">
				<div class="bank-box border rounded p-2 mb-3" style="
						background-color: var(--control-bg);
					">
					<p class="h5 flex align-center">
						{%= bank_account_list[i].bank_account_name %}
						{% if (bank_account_list[i].is_default) { %}
							<span class="text-muted">&nbsp;({%= __("Default") %})</span>
						{% } %}
						<a href="/app/Form/Bank Number/{%= encodeURIComponent(bank_account_list[i].name) %}"
							class="btn btn-xs btn-default ml-auto">
							{%= __("Edit") %}
						</a>
					</p>
					<p>
						{% if (bank_account_list[i].bank_number) { %}
							<strong>{%= __("Bank No") %}:</strong> {%= bank_account_list[i].bank_number %}<br>
						{% } %}
						{% if (bank_account_list[i].bank) { %}
							<strong>{%= __("Bank") %}:</strong> {%= bank_account_list[i].bank %}<br>
						{% } %}
						{% if (bank_account_list[i].branch) { %}
							<strong>{%= __("Branch") %}:</strong> {%= bank_account_list[i].branch %}<br>
						{% } %}
						{% if (bank_account_list[i].swift) { %}
							<strong>{%= __("SWIFT Code") %}:</strong> {%= bank_account_list[i].swift %}<br>
						{% } %}
					</p>
				</div>
			</div>
		{% } %}

		{% if (!bank_account_list.length) { %}
			<div class="col-sm-12">
				<p class="text-muted small">{%= __("No bank accounts added yet.") %}</p>
			</div>
		{% } %}
	</div>

	<p>
		<button class="btn btn-xs btn-default btn-bank-account">
			{{ __("New Bank Account") }}
		</button>
	</p>`
});
