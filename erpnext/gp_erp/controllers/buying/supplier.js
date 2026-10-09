frappe.ui.form.on("Supplier", {
	setup: function(frm) {
		frm.set_query("default_bank_account_no", function(doc) {
			return {
				filters: {
					"party": doc.name,
					"party_type": "Supplier"
				}
			}
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

	refresh: function(frm) {
		if (frm.doc.docstatus == 0) {
			// handled by standard
		} else {
			unhide_field(['bank_list_html']);
			frappe.contacts.render_address_and_contact(frm);
		}

		if(frm.flags.hard_reload){
			frm.reload_doc();
			frappe.flags.hard_reload = 0;
		}
	},

	supplier_code_series: function(frm) {
		frappe.call({
			method: "erpnext.buying.doctype.supplier.supplier.get_exists_series",
			args: {
				"series": frm.doc.supplier_code_series,
				"doctype": frm.doc.doctype,
				"name": frm.doc.name,
				"field_series": "supplier_code_series",
				"field_code": "supplier_code",
			},
			callback: function(r) {
				frm.set_value("supplier_code", r.message);
			}
		});
	},
});

// GP: extend frappe.contacts to include bank_list_html
frappe.provide("frappe.contacts");

$.extend(frappe.contacts, {
	clear_address_and_contact: function(frm) {
		$(frm.fields_dict["address_html"].wrapper).html("");
		frm.fields_dict["contact_html"] && $(frm.fields_dict["contact_html"].wrapper).html("");
		frm.fields_dict["bank_list_html"] && $(frm.fields_dict["bank_list_html"].wrapper).html("");
	},

	render_address_and_contact: function(frm) {
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
				.html(frappe.render_template(frappe.contacts.bank_account_list_template, frm.doc.__onload))
				.find(".btn-bank-account")
				.on("click", function () {
					frappe.new_doc("Bank Number", {
						party_type: frm.doctype,
						party: frm.doc.name
					});
				});
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
