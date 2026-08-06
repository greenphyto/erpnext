frappe.listview_settings['Request'] = {
    add_fields: [
        {fieldname:"item_name", parent:"Request Items"},
        {fieldname:"qty", parent:"Request Items"},
        {fieldname:"rate", parent:"Request Items"},
        {fieldname:"amount", parent:"Request Items"},
        {fieldname:"weight", parent:"Request Items"},
    ],
    hide_sidebar: 1,

    onload: function(listview) {
        listview.page.add_button(__("Bulk Upload"), function() {
            open_bulk_upload_dialog(listview);
        }, { btn_class: "btn-primary" });
    }
};

function open_bulk_upload_dialog(listview) {
    let csv_content = null;
    let parsed_data = null;
    let edits = {};

    const dialog = new frappe.ui.Dialog({
        title: __("Bulk Upload Request"),
        size: "extra-large",
        fields: [
            {
                fieldname: "upload_section",
                fieldtype: "HTML",
                label: __("Upload CSV")
            },
            {
                fieldname: "preview_section",
                fieldtype: "HTML",
                label: __("Preview")
            },
            {
                fieldname: "summary_html",
                fieldtype: "HTML",
                label: __("Summary")
            },
            {
                fieldname: "auto_submit",
                fieldtype: "Check",
                label: __("Auto Submit"),
                default: 0
            }
        ],
        primary_action_label: __("Generate"),
        primary_action: function() {
            if (!parsed_data || !parsed_data.groups || parsed_data.groups.length === 0) {
                frappe.msgprint(__("No data to generate"));
                return;
            }

            const auto_submit = dialog.get_value("auto_submit") ? 1 : 0;
            generate_requests(parsed_data, edits, auto_submit, dialog, listview);
        },
        secondary_action_label: __("Cancel"),
        secondary_action: function() {
            dialog.hide();
        }
    });

    dialog.show();

    // Render upload area
    const $upload_section = dialog.fields_dict.upload_section.$wrapper;
    $upload_section.html(`
        <div class="bulk-upload-area" style="border: 2px dashed #d1d8dd; border-radius: 8px; padding: 30px; text-align: center; margin-bottom: 15px; cursor: pointer; background: #fafbfc;">
            <div style="font-size: 36px; color: #b8c2cc; margin-bottom: 10px;">📁</div>
            <div style="font-size: 14px; color: #8d99a6;">${__("Drag CSV file here or click to upload")}</div>
            <input type="file" accept=".csv" style="display: none;" id="bulk-upload-csv-input">
        </div>
        <div id="bulk-upload-warnings" style="display: none; margin-top: 10px;"></div>
    `);

    const $upload_area = $upload_section.find('.bulk-upload-area');
    const $file_input = $upload_section.find('#bulk-upload-csv-input');

    // Click to upload
    $upload_area.on('click', function(e) {
        if (e.target === $file_input[0]) return;
        $file_input[0].click();
    });

    // Drag & drop
    $upload_area.on('dragover', function(e) {
        e.preventDefault();
        $(this).css('border-color', '#5e64ff').css('background', '#f0f0ff');
    });

    $upload_area.on('dragleave', function() {
        $(this).css('border-color', '#d1d8dd').css('background', '#fafbfc');
    });

    $upload_area.on('drop', function(e) {
        e.preventDefault();
        $(this).css('border-color', '#d1d8dd').css('background', '#fafbfc');
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            handle_file_upload(files[0]);
        }
    });

    // File input change
    $file_input.on('change', function() {
        if (this.files.length > 0) {
            handle_file_upload(this.files[0]);
        }
    });

    function handle_file_upload(file) {
        if (!file.name.endsWith('.csv')) {
            frappe.msgprint(__("Please upload a CSV file"));
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            csv_content = e.target.result;
            parse_csv_preview(csv_content);
        };
        reader.readAsText(file);
    }

    function parse_csv_preview(content) {
        frappe.dom.freeze(__("Parsing CSV..."));

        frappe.call({
            method: "erpnext.gp_erp.doctype.request.request.parse_forecast_upload",
            args: {
                csv_content: content
            },
            callback: function(r) {
                frappe.dom.unfreeze();

                if (r.message) {
                    parsed_data = r.message;
                    edits = {};
                    render_preview(parsed_data);
                    render_warnings(parsed_data.warnings);
                }
            },
            error: function(r) {
                frappe.dom.unfreeze();
                frappe.msgprint(__("Error parsing CSV: {0}", [r.message || "Unknown error"]));
            }
        });
    }

    function render_warnings(warnings) {
        const $warnings = $upload_section.find('#bulk-upload-warnings');
        if (!warnings || warnings.length === 0) {
            $warnings.hide();
            return;
        }

        let html = '<div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 10px; font-size: 12px;">';
        html += '<strong>⚠ ' + __('Warnings') + ' (' + warnings.length + '):</strong><br>';
        warnings.forEach(function(w) {
            html += '<div style="color: #856404; margin-top: 3px;">Row ' + w.row + ': ' + w.message + '</div>';
        });
        html += '</div>';
        $warnings.html(html).show();
    }

    function render_preview(data) {
        const $preview = dialog.fields_dict.preview_section.$wrapper;
        const $summary = dialog.fields_dict.summary_html.$wrapper;

        if (!data.groups || data.groups.length === 0) {
            $preview.html('<div style="text-align: center; padding: 20px; color: #8d99a6;">' + __('No data to preview') + '</div>');
            $summary.html('');
            return;
        }

        let html = '<div style="max-height: 450px; overflow-y: auto;">';

        data.groups.forEach(function(group, group_idx) {
            const group_id = 'group-' + group_idx;
            html += '<div class="bulk-group" style="margin-bottom: 10px; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden;">';

            // Group header (collapsible)
            const days_label = group.days_to_delivery >= 0 ? group.days_to_delivery + ' days' : Math.abs(group.days_to_delivery) + ' days ago';
            html += '<div class="bulk-group-header" data-group="' + group_idx + '" style="background: #f8f9fa; padding: 8px 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 13px;">';
            html += '<span>▼ ' + group.delivery_date + ' (' + days_label + ') — ' + group.customer + ' (' + group.items.length + ' items)</span>';
            html += '<span class="group-total" data-group="' + group_idx + '" style="font-weight: normal; color: #6c757d;"></span>';
            html += '</div>';

            // Group body
            html += '<div class="bulk-group-body" id="' + group_id + '" style="overflow-x: auto;">';
            html += '<table style="width: 100%; border-collapse: collapse; font-size: 12px; table-layout: fixed;">';
            html += '<colgroup>';
            html += '<col style="width: 15%;">';  // Item
            html += '<col style="width: 18%;">';  // Vegetable
            html += '<col style="width: 8%;">';   // Qty
            html += '<col style="width: 12%;">';  // Packaging
            html += '<col style="width: 11%;">';  // Total Kg
            html += '<col style="width: 11%;">';  // Rate
            html += '<col style="width: 15%;">';  // Amount
            html += '<col style="width: 10%;">';  // Action
            html += '</colgroup>';
            html += '<thead><tr style="background: #f1f3f5;">';
            html += '<th style="padding: 6px 8px; text-align: left; border-bottom: 1px solid #dee2e6; overflow: hidden; text-overflow: ellipsis;">' + __('Item') + '</th>';
            html += '<th style="padding: 6px 8px; text-align: left; border-bottom: 1px solid #dee2e6; overflow: hidden; text-overflow: ellipsis;">' + __('Vegetable') + '</th>';
            html += '<th style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #dee2e6;">' + __('Qty') + '</th>';
            html += '<th style="padding: 6px 8px; text-align: left; border-bottom: 1px solid #dee2e6; overflow: hidden; text-overflow: ellipsis;">' + __('Packaging') + '</th>';
            html += '<th style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #dee2e6;">' + __('Total Kg') + '</th>';
            html += '<th style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #dee2e6;">' + __('Rate') + '</th>';
            html += '<th style="padding: 6px 8px; text-align: right; border-bottom: 1px solid #dee2e6;">' + __('Amount') + '</th>';
            html += '<th style="padding: 6px 8px; text-align: center; border-bottom: 1px solid #dee2e6;">' + __('Action') + '</th>';
            html += '</tr></thead>';
            html += '<tbody>';

            group.items.forEach(function(item, item_idx) {
                const amount = (item.qty || 0) * (item.rate || 0);
                const total_kg = item.total_kg || 0;
                const escaped_warning = item.warning ? $('<span>').text(item.warning).html() : '';
                const warning_class = escaped_warning ? ' style="background: #fff3cd;"' : '';
                const disabled = escaped_warning ? ' disabled' : '';
                const warning_title = escaped_warning ? ' title="' + escaped_warning + '"' : '';

                html += '<tr class="bulk-item-row" data-group="' + group_idx + '" data-item="' + item_idx + '"' + warning_class + '>';
                html += '<td style="padding: 6px 8px; border-bottom: 1px solid #eee; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"' + warning_title + '>' + (escaped_warning ? '⚠ ' : '') + (item.item_code || '-') + '</td>';
                html += '<td style="padding: 6px 8px; border-bottom: 1px solid #eee; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">' + (item.vegetable || '-') + '</td>';
                html += '<td style="padding: 6px 8px; border-bottom: 1px solid #eee; text-align: right;">';
                html += '<input type="number" class="bulk-qty-input" data-group="' + group_idx + '" data-item="' + item_idx + '" value="' + (item.qty || 0) + '" style="width: 100%; text-align: right; border: 1px solid #d1d8dd; border-radius: 3px; padding: 3px 5px; box-sizing: border-box;"' + disabled + '>';
                html += '</td>';
                html += '<td style="padding: 6px 8px; border-bottom: 1px solid #eee; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">' + (item.packaging || '-') + '</td>';
                html += '<td style="padding: 6px 8px; border-bottom: 1px solid #eee; text-align: right;" class="bulk-total-kg" data-group="' + group_idx + '" data-item="' + item_idx + '">' + total_kg.toFixed(2) + '</td>';
                html += '<td style="padding: 6px 8px; border-bottom: 1px solid #eee; text-align: right;">' + (item.rate || 0).toFixed(2) + '</td>';
                html += '<td style="padding: 6px 8px; border-bottom: 1px solid #eee; text-align: right;" class="bulk-amount" data-group="' + group_idx + '" data-item="' + item_idx + '">' + amount.toFixed(2) + '</td>';
                html += '<td style="padding: 6px 8px; border-bottom: 1px solid #eee; text-align: center;">';
                html += '<button class="btn btn-xs btn-default bulk-delete-row" data-group="' + group_idx + '" data-item="' + item_idx + '"' + disabled + '>✕</button>';
                html += '</td>';
                html += '</tr>';
            });

            html += '</tbody></table>';
            html += '</div></div>';
        });

        html += '</div>';
        $preview.html(html);

        update_summary(data);

        // Toggle group collapse
        $preview.find('.bulk-group-header').on('click', function() {
            const group_idx = $(this).data('group');
            const $body = $preview.find('#group-' + group_idx);
            const $icon = $(this).find('span:first');
            if ($body.is(':visible')) {
                $body.hide();
                $icon.html('▶ ' + $icon.text().replace('▼ ', ''));
            } else {
                $body.show();
                $icon.html('▼ ' + $icon.text().replace('▶ ', ''));
            }
        });

        // Qty change handler
        $preview.find('.bulk-qty-input').on('change', function() {
            const group_idx = $(this).data('group');
            const item_idx = $(this).data('item');
            const new_qty = flt($(this).val()) || 0;

            // Track edit
            if (!edits[group_idx]) edits[group_idx] = {};
            edits[group_idx][item_idx] = { qty: new_qty };

            // Update amount and total_kg display
            const item = parsed_data.groups[group_idx].items[item_idx];
            const rate = item.rate || 0;
            const unit_weight = item.unit_weight || 0;
            const amount = new_qty * rate;
            const total_kg = new_qty * unit_weight;
            $preview.find('.bulk-amount[data-group="' + group_idx + '"][data-item="' + item_idx + '"]').text(amount.toFixed(2));
            $preview.find('.bulk-total-kg[data-group="' + group_idx + '"][data-item="' + item_idx + '"]').text(total_kg.toFixed(2));

            // Update data model
            item.qty = new_qty;
            item.total_kg = Math.round(total_kg * 100) / 100;

            update_summary(parsed_data);
        });

        // Delete row handler
        $preview.find('.bulk-delete-row').on('click', function() {
            const group_idx = $(this).data('group');
            const item_idx = $(this).data('item');

            // Remove from data model
            parsed_data.groups[group_idx].items.splice(item_idx, 1);

            // Remove row from DOM
            $(this).closest('tr').remove();

            // Re-index remaining rows in this group
            $preview.find('.bulk-item-row[data-group="' + group_idx + '"]').each(function(new_idx) {
                $(this).data('item', new_idx);
                $(this).find('.bulk-qty-input').data('item', new_idx);
                $(this).find('.bulk-delete-row').data('item', new_idx);
                $(this).find('.bulk-amount').data('item', new_idx);
            });

            // Clean up edits for this group
            delete edits[group_idx];

            // Remove group if empty
            if (parsed_data.groups[group_idx].items.length === 0) {
                parsed_data.groups.splice(group_idx, 1);
                $preview.find('.bulk-group').eq(group_idx).remove();
                // Re-index groups
                $preview.find('.bulk-group').each(function(new_gidx) {
                    $(this).find('.bulk-group-header').data('group', new_gidx);
                    $(this).find('.bulk-group-body').attr('id', 'group-' + new_gidx);
                });
                // Re-key edits: shift down all edits with index > deleted group_idx
                const new_edits = {};
                for (const [oldIdx, editData] of Object.entries(edits)) {
                    const oldIdxNum = parseInt(oldIdx);
                    if (oldIdxNum === group_idx) continue; // deleted group
                    if (oldIdxNum > group_idx) {
                        new_edits[oldIdxNum - 1] = editData; // shift down
                    } else {
                        new_edits[oldIdxNum] = editData; // keep as-is
                    }
                }
                // Clear and reassign
                for (const key of Object.keys(edits)) {
                    delete edits[key];
                }
                Object.assign(edits, new_edits);
            }

            update_summary(parsed_data);
        });
    }

    function update_summary(data) {
        const $summary = dialog.fields_dict.summary_html.$wrapper;
        if (!data || !data.groups) {
            $summary.html('');
            return;
        }

        let total_groups = 0;
        let total_items = 0;

        data.groups.forEach(function(group) {
            if (group.items.length > 0) {
                total_groups++;
                total_items += group.items.length;
            }
        });

        $summary.html(
            '<div style="padding: 8px 12px; background: #f8f9fa; border-radius: 4px; font-size: 13px; color: #495057;">' +
            '<strong>' + __('Summary') + ':</strong> ' +
            total_groups + ' ' + __('Requests') + ', ' +
            total_items + ' ' + __('items') +
            '</div>'
        );
    }

    function generate_requests(data, edits, auto_submit, dialog, listview) {
        frappe.dom.freeze(__("Generating Requests..."));

        frappe.call({
            method: "erpnext.gp_erp.doctype.request.request.generate_bulk_requests",
            args: {
                groups: JSON.stringify(data.groups),
                edits: JSON.stringify(edits),
                auto_submit: auto_submit
            },
            callback: function(r) {
                frappe.dom.unfreeze();

                if (r.message) {
                    const result = r.message;
                    let msg = '<div style="padding: 10px;">';

                    if (result.created && result.created.length > 0) {
                        msg += '<p><strong>✅ ' + __('Created') + ' (' + result.created.length + '):</strong></p>';
                        msg += '<ul style="max-height: 150px; overflow-y: auto;">';
                        result.created.forEach(function(name) {
                            const safe_name = $('<span>').text(name).html();
                            msg += '<li><a href="/app/request/' + safe_name + '">' + safe_name + '</a></li>';
                        });
                        msg += '</ul>';
                    }

                    if (result.merged && result.merged.length > 0) {
                        msg += '<p><strong>🔗 ' + __('Merged') + ' (' + result.merged.length + '):</strong></p>';
                        msg += '<ul style="max-height: 150px; overflow-y: auto;">';
                        result.merged.forEach(function(m) {
                            const safe_name = $('<span>').text(m.name).html();
                            const safe_items = m.added_items.map(function(i) {
                                return $('<span>').text(i).html();
                            }).join(', ');
                            msg += '<li><a href="/app/request/' + safe_name + '">' + safe_name + '</a> — ' +
                                __('Added') + ': ' + safe_items + '</li>';
                        });
                        msg += '</ul>';
                    }

                    if (result.errors && result.errors.length > 0) {
                        msg += '<p><strong>❌ ' + __('Errors') + ' (' + result.errors.length + '):</strong></p>';
                        msg += '<ul style="max-height: 150px; overflow-y: auto;">';
                        result.errors.forEach(function(e) {
                            const safe_group = $('<span>').text(e.group).html();
                            const safe_error = $('<span>').text(e.error).html();
                            msg += '<li><strong>' + safe_group + ':</strong> ' + safe_error + '</li>';
                        });
                        msg += '</ul>';
                    }

                    // No created, merged, or errors — already inserted
                    const no_created = !result.created || result.created.length === 0;
                    const no_merged = !result.merged || result.merged.length === 0;
                    const no_errors = !result.errors || result.errors.length === 0;
                    if (no_created && no_merged && no_errors) {
                        msg += '<p style="text-align: center; color: #8d99a6; padding: 20px 0;">' + __('Already Inserted') + '</p>';
                    }

                    msg += '</div>';

                    frappe.msgprint({
                        title: __("Bulk Upload Result"),
                        indicator: result.errors && result.errors.length > 0 ? "orange" : "green",
                        message: msg
                    });

                    dialog.hide();
                    listview.refresh();
                }
            },
            error: function(r) {
                frappe.dom.unfreeze();
                frappe.msgprint(__("Error generating requests: {0}", [r.message || "Unknown error"]));
            }
        });
    }
}