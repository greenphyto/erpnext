frappe.ui.form.on("Customer", {
    is_cash_sales: function(frm) {
        var cash_sales = "C00008";
        frappe.db.get_value("Company", frm.doc.company, "series_abbr").then(r => {
            if (frm.doc.is_cash_sales) {
                cash_sales = cstr(r.message.series_abbr) + cash_sales;
                frm.set_value("customer_code", cash_sales);
            } else {
                frm.set_value("customer_code", "");
            }
        });
    },
    get_all_product: function(frm) {
        frappe.call({
            method: 'erpnext.gp_erp.controllers.selling.customer.get_all_product',
            args: { customer: frm.doc.name },
            callback: function(r) {
                const rows = r.message || [];
                if (!rows.length) {
                    frappe.msgprint(__('No product rows found.'));
                    return;
                }
                const existing_rows = frm.doc.customer_packaging || [];
                const row_key = d => `${d.item_code || ''}::${d.package || ''}`;
                const existing_map = new Map();
                existing_rows.forEach(row => {
                    const key = row_key(row);
                    if (!existing_map.has(key)) existing_map.set(key, []);
                    existing_map.get(key).push(row);
                });
                const rows_html = rows.map((d, idx) => {
                    const key = row_key(d);
                    const is_existing = existing_map.has(key);
                    return `<tr class="customer-packaging-row ${is_existing ? 'table-active' : ''}" data-key="${frappe.utils.escape_html(key)}" style="cursor:pointer;">
                        <td class="text-center" style="width: 48px;"><input type="checkbox" class="customer-packaging-row-check" ${is_existing ? 'checked' : ''}></td>
                        <td>${frappe.utils.escape_html(d.item_code || '')}</td>
                        <td>${frappe.utils.escape_html(d.item_name || '')}</td>
                        <td>${frappe.utils.escape_html(d.package || '')}</td>
                        <td>${frappe.utils.escape_html(d.packaging || '')}</td>
                    </tr>`;
                }).join('');
                const dialog = new frappe.ui.Dialog({
                    title: __('Select Products for Customer Packaging'),
                    fields: [{ fieldname: 'items_html', fieldtype: 'HTML' }],
                    size: "large",
                    primary_action_label: __('Save Selection'),
                    primary_action() {
                        const selected_keys = new Set();
                        dialog.$wrapper.find('.customer-packaging-row-check:checked').each(function() {
                            const key = $(this).closest('tr').attr('data-key');
                            if (key) selected_keys.add(key);
                        });
                        const rows_to_add = rows.filter(row => !existing_map.has(row_key(row)) && selected_keys.has(row_key(row)));
                        rows_to_add.forEach(parsed => {
                            const child = frm.add_child('customer_packaging');
                            child.item_code = parsed.item_code;
                            child.item_name = parsed.item_name;
                            child.package = parsed.package;
                            child.packaging = parsed.packaging;
                            child.carton_uom = 'Carton';
                            child.carton_size = frm.doc.default_carton_size || 12;
                        });
                        if (rows_to_add.length) frm.refresh_field('customer_packaging');
                        dialog.hide();
                    }
                });
                dialog.fields_dict.items_html.$wrapper.html(`<div class="table-responsive"><table class="table table-bordered table-striped"><thead><tr><th style="width:20px;">${__('Select')}</th><th>${__('Item Code')}</th><th>${__('Item Name')}</th><th>${__('Package')}</th><th>${__('Packaging')}</th></tr></thead><tbody>${rows_html}</tbody></table></div>`);
                dialog.show();
                dialog.$wrapper.on('click', '.customer-packaging-row', function(e) {
                    if ($(e.target).is('input, button, a, label')) return;
                    const checkbox = $(this).find('.customer-packaging-row-check');
                    checkbox.prop('checked', !checkbox.is('checked'));
                    $(this).toggleClass('table-active', checkbox.is(':checked'));
                });
            }
        });
    },
    update_carton_size: function(frm) {
        const rows = frm.doc.customer_packaging || [];
        if (!rows.length) { frappe.msgprint(__('No Customer Packaging rows to update.')); return; }
        frappe.confirm(
            __('Update carton size to <b>{0}</b> for {1} row(s)?', [frm.doc.default_carton_size, rows.length]),
            () => { rows.forEach(row => { row.carton_size = frm.doc.default_carton_size; }); frm.refresh_field('customer_packaging'); }
        );
    }
});

frappe.ui.form.on("Customer Packaging Detail", {
    customer_packaging_add: function(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, "carton_uom", "Carton");
        frappe.model.set_value(cdt, cdn, "carton_size", frm.doc.default_carton_size || 12);
    },
    item_code: function(frm, cdt, cdn) { frm.cscript.validate_package_unique && frm.cscript.validate_package_unique(frm, cdt, cdn); },
    package: function(frm, cdt, cdn) { frm.cscript.validate_package_unique && frm.cscript.validate_package_unique(frm, cdt, cdn); }
});

$.extend(cur_frm.cscript, {
    validate_package_unique: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code || !row.package) return;
        const duplicate = (frm.doc.customer_packaging || []).find(d => d.name !== row.name && d.item_code === row.item_code && d.package === row.package);
        if (duplicate) {
            frappe.msgprint(__('Item {0} with package {1} already added', [row.item_code, row.package]));
            frappe.model.set_value(cdt, cdn, "package", null);
        }
    }
});
