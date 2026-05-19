// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Customer", {
	setup: function(frm) {

		frm.make_methods = {
			'Quotation': () => frappe.model.open_mapped_doc({
				method: "erpnext.selling.doctype.customer.customer.make_quotation",
				frm: cur_frm
			}),
			'Opportunity': () => frappe.model.open_mapped_doc({
				method: "erpnext.selling.doctype.customer.customer.make_opportunity",
				frm: cur_frm
			})
		}

		frm.add_fetch('lead_name', 'company_name', 'customer_name');
		frm.add_fetch('default_sales_partner','commission_rate','default_commission_rate');
		frm.set_query('customer_group', {'is_group': 0});
		frm.set_query('default_price_list', { 'selling': 1});
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			var filters = {
				'account_type': 'Receivable',
				'company': d.company,
				"is_group": 0
			};

			if(doc.party_account_currency) {
				$.extend(filters, {"account_currency": doc.party_account_currency});
			}
			return {
				filters: filters
			}
		});

		if (frm.doc.__islocal == 1) {
			frm.set_value("represents_company", "");
		}

		frm.set_query('customer_primary_contact', function(doc) {
			return {
				query: "erpnext.selling.doctype.customer.customer.get_customer_primary_contact",
				filters: {
					'customer': doc.name
				}
			}
		})
		frm.set_query('customer_primary_address', function(doc) {
			return {
				filters: {
					'link_doctype': 'Customer',
					'link_name': doc.name
				}
			}
		})

		frm.set_query('default_bank_account', function() {
			return {
				filters: {
					'is_company_account': 1
				}
			}
		});
	},
	is_cash_sales: function(frm){
		var cash_sales = "C00008"
		frappe.db.get_value("Company", frm.doc.company, "series_abbr").then(r=>{
			console.log(70, r)
			if (frm.doc.is_cash_sales){
				cash_sales = cstr(r.message.series_abbr) + cash_sales
				frm.set_value("customer_code", cash_sales);
			}else{
				frm.set_value("customer_code", "")
			}
		})
	},
	customer_primary_address: function(frm){
		if(frm.doc.customer_primary_address){
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: {
					"address_dict": frm.doc.customer_primary_address
				},
				callback: function(r) {
					frm.set_value("primary_address", r.message);
				}
			});
		}
		if(!frm.doc.customer_primary_address){
			frm.set_value("primary_address", "");
		}
	},

	is_internal_customer: function(frm) {
		if (frm.doc.is_internal_customer == 1) {
			frm.toggle_reqd("represents_company", true);
		}
		else {
			frm.toggle_reqd("represents_company", false);
		}
	},

	customer_primary_contact: function(frm){
		if(!frm.doc.customer_primary_contact){
			frm.set_value("mobile_no", "");
			frm.set_value("email_id", "");
		}
	},

	loyalty_program: function(frm) {
		if(frm.doc.loyalty_program) {
			frm.set_value('loyalty_program_tier', null);
		}
	},

	refresh: function(frm) {
		if(frappe.defaults.get_default("cust_master_name")!="Naming Series") {
			frm.toggle_display("naming_series", false);
		} else {
			erpnext.toggle_naming_series();
		}

		frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Customer'}

		if(!frm.doc.__islocal) {
			frappe.contacts.render_address_and_contact(frm);

			// custom buttons

			frm.add_custom_button(__('Accounts Receivable'), function () {
				frappe.set_route('query-report', 'Accounts Receivable', {customer:frm.doc.name});
			}, __('View'));

			frm.add_custom_button(__('Accounting Ledger'), function () {
				frappe.set_route('query-report', 'General Ledger',
					{party_type: 'Customer', party: frm.doc.name});
			}, __('View'));

			frm.add_custom_button(__('Pricing Rule'), function () {
				erpnext.utils.make_pricing_rule(frm.doc.doctype, frm.doc.name);
			}, __('Create'));

			frm.add_custom_button(__('Get Customer Group Details'), function () {
				frm.trigger("get_customer_group_details");
			}, __('Actions'));

			if (cint(frappe.defaults.get_default("enable_common_party_accounting"))) {
				frm.add_custom_button(__('Link with Supplier'), function () {
					frm.trigger('show_party_link_dialog');
				}, __('Actions'));
			}

			// indicator
			erpnext.utils.set_party_dashboard_indicators(frm);

		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		var grid = cur_frm.get_field("sales_team").grid;
		grid.set_column_disp("allocated_amount", false);
		grid.set_column_disp("incentives", false);

		frm.set_query("item_code", "customer_packaging", function() {
			return {
				filters: {
					"item_group": "Products",
					"disabled": 0
				}
			}
		})
		frm.set_query("carton_uom", "customer_packaging", function() {
			return {
				filters: {
					"is_carton": 1,
					"enabled": 1
				}
			}
		})
		frm.set_query("packaging", "customer_packaging", function() {
			return {
				filters: {
					"material_group": "Other Packaging",
					"disabled": 0
				}
			}
		})

		frm.set_query("package", "customer_packaging", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			if (!row.item_code) frappe.throw(__("Please select Item"));
			var args =  erpnext.queries.uom({
				"parent": row.item_code,
				"is_packaging": 1
			})

			return args;
		});
	},
	validate: function(frm) {
		if(frm.doc.lead_name) frappe.model.clear_doc("Lead", frm.doc.lead_name);

	},
	get_customer_group_details: function(frm) {
		frappe.call({
			method: "get_customer_group_details",
			doc: frm.doc,
			callback: function() {
				frm.refresh();
			}
		});

	},
	show_party_link_dialog: function(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __('Select a Supplier'),
			fields: [{
				fieldtype: 'Link', label: __('Supplier'),
				options: 'Supplier', fieldname: 'supplier', reqd: 1
			}],
			primary_action: function({ supplier }) {
				frappe.call({
					method: 'erpnext.accounts.doctype.party_link.party_link.create_party_link',
					args: {
						primary_role: 'Customer',
						primary_party: frm.doc.name,
						secondary_party: supplier
					},
					freeze: true,
					callback: function() {
						dialog.hide();
						frappe.msgprint({
							message: __('Successfully linked to Supplier'),
							alert: true
						});
					},
					error: function() {
						dialog.hide();
						frappe.msgprint({
							message: __('Linking to Supplier Failed. Please try again.'),
							title: __('Linking Failed'),
							indicator: 'red'
						});
					}
				});
			},
			primary_action_label: __('Create Link')
		});
		dialog.show();
	},
	get_all_product: function(frm) {
		frappe.call({
			method: 'erpnext.selling.doctype.customer.customer.get_all_product',
			args: {
				customer: frm.doc.name
			},
			callback: function(r) {
				const rows = r.message || [];
				const existing_rows = frm.doc.customer_packaging || [];
				const row_key = d => `${d.item_code || ''}::${d.package || ''}`;

				const existing_map = new Map();
				existing_rows.forEach(row => {
					const key = row_key(row);
					if (!existing_map.has(key)) {
						existing_map.set(key, []);
					}
					existing_map.get(key).push(row);
				});

				if (!rows.length) {
					frappe.msgprint(__('No product rows found.'));
					return;
				}

				const rows_html = rows.map((d, idx) => {
					const key = row_key(d);
					const is_existing = existing_map.has(key);
					const item_code = frappe.utils.escape_html(d.item_code || '');
					const item_name = frappe.utils.escape_html(d.item_name || '');
					const package_name = frappe.utils.escape_html(d.package || '');
					const packaging = frappe.utils.escape_html(d.packaging || '');
					return `
						<tr class="customer-packaging-row ${is_existing ? 'table-active' : ''}" data-index="${idx}" data-key="${frappe.utils.escape_html(key)}" style="cursor:pointer;">
							<td class="text-center" style="width: 48px;">
								<input type="checkbox" class="customer-packaging-row-check" ${is_existing ? 'checked' : ''}>
							</td>
							<td>${item_code}</td>
							<td>${item_name}</td>
							<td>${package_name}</td>
							<td>${packaging}</td>
						</tr>`;
				}).join('');

				const dialog = new frappe.ui.Dialog({
					title: __('Select Products for Customer Packaging'),
					fields: [
						{
							fieldname: 'items_html',
							fieldtype: 'HTML'
						}
					],
					size: "large",
					primary_action_label: __('Save Selection'),
					primary_action(values) {
						const selected_keys = new Set();
						dialog.$wrapper.find('.customer-packaging-row-check:checked').each(function() {
							const key = $(this).closest('tr').attr('data-key');
							if (key) {
								selected_keys.add(key);
							}
						});

						const rows_to_add = rows.filter(row => !existing_map.has(row_key(row)) && selected_keys.has(row_key(row)));
						const rows_to_delete = existing_rows.filter(row => !selected_keys.has(row_key(row)));

						rows_to_add.forEach(parsed => {
							const child = frm.add_child('customer_packaging');
							child.item_code = parsed.item_code;
							child.item_name = parsed.item_name;
							child.package = parsed.package;
							child.packaging = parsed.packaging;
							child.carton_uom = 'Carton';
							child.carton_size = frm.doc.default_carton_size || 12;
						});

						if (rows_to_add.length) {
							frm.refresh_field('customer_packaging');
						}

						if (!rows_to_delete.length) {
							dialog.hide();
							return;
						}

						dialog.hide();

						const delete_list_html = rows_to_delete.map(row => {
							const parts = [
								frappe.utils.escape_html(row.item_code || ''),
								frappe.utils.escape_html(row.item_name || ''),
								frappe.utils.escape_html(row.package || ''),
								frappe.utils.escape_html(row.packaging || '')
							];
							var deleted_text = `Item ${parts[0]} with Package ${parts[2]}`;
							return `<li>${deleted_text}</li>`;
						}).join('');

						frappe.confirm(
							`${__('The following rows will be deleted from table:')}<br><ul>${delete_list_html}</ul>`,
							() => {
								const delete_keys = new Set(rows_to_delete.map(row_key));
								(frm.doc.customer_packaging || []).slice().forEach(row => {
									if (delete_keys.has(row_key(row))) {
										frappe.model.clear_doc(row.doctype, row.name);
									}
								});

								frm.doc.customer_packaging = (frm.doc.customer_packaging || []).filter(row => !delete_keys.has(row_key(row)));
								frm.refresh_field('customer_packaging');
								dialog.hide();
							}
						);
					}
				});

				const html = `
					<div class="table-responsive">
						<table class="table table-bordered table-striped">
							<thead>
								<tr>
									<th style="width:20px;">${__('Select')}</th>
									<th style="width:15%;">${__('Item Code')}</th>
									<th style="width:30%;">${__('Item Name')}</th>
									<th style="width:30%;">${__('Package')}</th>
									<th style="width:16%;">${__('Packaging')}</th>
								</tr>
							</thead>
							<tbody>
								${rows_html}
							</tbody>
						</table>
					</div>`;

				const field = dialog.fields_dict.items_html;
				field.$wrapper.html(html);

				const sync_row_state = row => {
					const checkbox = row.find('.customer-packaging-row-check');
					row.toggleClass('table-active', checkbox.is(':checked'));
				};

				dialog.show();

				dialog.$wrapper.on('click', '.customer-packaging-row', function(e) {
					if ($(e.target).is('input, button, a, label')) {
						return;
					}
					const row = $(this);
					const checkbox = row.find('.customer-packaging-row-check');
					checkbox.prop('checked', !checkbox.is(':checked'));
					sync_row_state(row);
				});

				dialog.$wrapper.on('click', '.customer-packaging-row-check', function(e) {
					e.stopPropagation();
					const row = $(this).closest('tr');
					sync_row_state(row);
				});

				dialog.$wrapper.find('.customer-packaging-row').each(function() {
					sync_row_state($(this));
				});

			}
		});
	},
	update_carton_size: function(frm) {
		const rows = frm.doc.customer_packaging || [];
		if (!rows.length) {
			frappe.msgprint(__('No Customer Packaging rows to update.'));
			return;
		}

		const new_carton_size = frm.doc.default_carton_size;
		frappe.confirm(
			__('Update carton size to <b>{0}</b> for {1} row(s)?', [new_carton_size, rows.length]),
			() => {
				rows.forEach(row => {
					row.carton_size = new_carton_size;
				});
				frm.refresh_field('customer_packaging');
			}
		);
	}
});

frappe.ui.form.on("Customer Packaging Detail", {
	customer_packaging_add: function(frm, cdt, cdn) {	
		frappe.model.set_value(cdt, cdn, "carton_uom", "Carton");
		frappe.model.set_value(cdt, cdn, "carton_size", frm.doc.default_carton_size || 12);
	},
	item_code: function(frm, cdt, cdn) {
		frm.cscript.validate_package_unique(frm, cdt, cdn);
	},
	package: function(frm, cdt, cdn) {
		frm.cscript.validate_package_unique(frm, cdt, cdn);
	},
})

$.extend(cur_frm.cscript, {
	validate_package_unique: function(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code || !row.package) {
			return;
		}

		const duplicate = (frm.doc.customer_packaging || []).find(d => {
			return d.name !== row.name && d.item_code === row.item_code && d.package === row.package;
		});

		if (duplicate) {
			frappe.msgprint(__('Item ${0} with package ${1} already added', [row.item_code, row.package]));
			frappe.model.set_value(cdt, cdn, "package", null);
		}
	}
})