frappe.pages['payment-bulk-approval'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Payment Bulk Approval',
        single_column: true,
    });

    // Back to native List view
    page.set_secondary_action(__('Back to Payment Approval'), function () {
        frappe.set_route('List', 'Payment Approval');
    });

    // Reload action (top-right)
    page.set_primary_action(__('Reload'), function () {
        if (paging && paging.loading) return;
        reset_and_load().then(() => {
            frappe.show_alert('Done refresh');
        });
    }, 'refresh');

    // Main container
    const $container = $(`
        <div class="payment-bulk-approval">
            <style>
                .payment-bulk-approval .frappe-card { width: 100%; }
                .payment-bulk-approval table { width: 100% !important; table-layout: fixed; }
                .payment-bulk-approval th, .payment-bulk-approval td { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
                .payment-bulk-approval .action-cell { white-space: nowrap; padding: 6px; }
                .payment-bulk-approval .action-cell .action-wrapper { display: flex; justify-content: center; align-items: center; gap: 8px; width: 100%; }
                .payment-bulk-approval .toggle-detail { padding: 2px 6px; line-height: 1; margin-right: 6px; }
                /* Row striping */
                .payment-bulk-approval tr.data-row.odd td { background: #fff1d8; }
                .payment-bulk-approval tr.data-row.even td { background: #ffddb4; }
                /* Collapsible detail styling tied to parent row */
                .payment-bulk-approval tr.detail-row.belongs-odd td { background: #fff7e6; border-left: 4px solid #fff1d8; }
                .payment-bulk-approval tr.detail-row.belongs-even td { background: #ffe9d1; border-left: 4px solid #ffddb4; }
                .payment-bulk-approval .detail-body { padding: 8px 12px; }
                .payment-bulk-approval .detail-table { width: 100%; table-layout: auto; }
                .payment-bulk-approval .controls { display: flex; align-items: center; gap: 16px; }
                .payment-bulk-approval .filter-bar { margin-top: 8px; }
                .payment-bulk-approval .filters-grid { display: grid; grid-template-columns: repeat(3, minmax(220px, 1fr)); gap: 8px 16px; }
                .payment-bulk-approval .filters-actions { display:flex; gap: 8px; margin-top: 8px; }
                .payment-bulk-approval .list-footer { display:flex; justify-content:center; align-items:center; padding: 8px; position: relative; }
                .payment-bulk-approval .btn-load-more { min-width: 160px; }
                .payment-bulk-approval .list-count { position: absolute; right: 8px; color: var(--text-muted); font-size: 12px; }
            </style>
            <div class="mb-4">
                <div class="filter-bar">
                    <div class="filters-grid"></div>
                    <div class="filters-actions">
                        <button class="btn btn-sm btn-primary apply-filters">Apply</button>
                        <button class="btn btn-sm btn-default clear-filters">Clear</button>
                    </div>
                </div>
				<br>
				<div class="controls mt-4">
                    <label class="mb-0 text-muted">
                        <input type="checkbox" class="show-all-details" />
                        <span>Show all details</span>
                    </label>
                </div>
            </div>
            <div class="frappe-card">
                <div class="frappe-card-body" style="padding: 0;">
                    <div class="list-table-wrapper">
                        <table class="table table-bordered table-hover">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Posting Date</th>
                                    <th>Time</th>
                                    <th>Requested By</th>
                                    <th>Payment Type</th>
                                    <th class="text-right">Total Amount</th>
                                    <th>Bank Account</th>
                                    <th>Currency</th>
                                    <th class="text-center">Action</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                        <div class="list-footer">
                            <button class="btn btn-default btn-sm btn-load-more" style="display:none;">Load more</button>
                            <div class="list-count" style="display:none;"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);

    $(page.body).empty().append($container);

    const $tbody = $container.find('tbody');
    const $loadMore = $container.find('.btn-load-more');
    const $count = $container.find('.list-count');
    const $showAll = $container.find('.show-all-details');
    const $filtersGrid = $container.find('.filters-grid');
    const $applyBtn = $container.find('.apply-filters');
    const $clearBtn = $container.find('.clear-filters');
    let showAll = false;
    const paging = { start: 0, page_length: 20, has_more: false, loading: false };
    const filterControls = {};

    // Build report-style filters
    const filterDefs = [
        { fieldname: 'posting_date_from', label: 'Posting Date From', fieldtype: 'Date' },
        { fieldname: 'posting_date_to', label: 'Posting Date To', fieldtype: 'Date' },
        { fieldname: 'requested_by', label: 'Requested By', fieldtype: 'Link', options: 'User' },
        { fieldname: 'bank_account', label: 'Bank Account', fieldtype: 'Link', options: 'Bank Account' },
        { fieldname: 'currency', label: 'Currency', fieldtype: 'Link', options: 'Currency' },
        { fieldname: 'approval_id', label: 'Approval ID', fieldtype: 'Data' },
        { fieldname: 'amount_min', label: 'Amount Min', fieldtype: 'Float' },
        { fieldname: 'amount_max', label: 'Amount Max', fieldtype: 'Float' },
    ];
    filterDefs.forEach(def => {
        const $wrap = $('<div></div>').appendTo($filtersGrid);
        const ctrl = frappe.ui.form.make_control({
            parent: $wrap,
            df: Object.assign({
                name: def.fieldname,
                fieldname: def.fieldname,
                label: __(def.label),
                fieldtype: def.fieldtype,
                options: def.options || undefined,
                reqd: false,
                onchange: () => {},
            }, def)
        });
        ctrl.refresh();
        filterControls[def.fieldname] = ctrl;
    });

    // Helpers to manage default posting dates
    function set_default_dates() {
        try {
            const today = frappe.datetime.get_today();
            const from = frappe.datetime.add_months(today, -3);
            if (filterControls.posting_date_from && filterControls.posting_date_from.set_value) {
                filterControls.posting_date_from.set_value(from);
            }
            if (filterControls.posting_date_to && filterControls.posting_date_to.set_value) {
                filterControls.posting_date_to.set_value(today);
            }
        } catch (e) {
            // ignore default errors
        }
    }

    // Apply defaults on load
    set_default_dates();

    function get_filters_payload() {
        const val = {};
        val.posting_date_from = filterControls.posting_date_from && filterControls.posting_date_from.get_value && filterControls.posting_date_from.get_value();
        val.posting_date_to = filterControls.posting_date_to && filterControls.posting_date_to.get_value && filterControls.posting_date_to.get_value();
        val.requested_by = filterControls.requested_by && filterControls.requested_by.get_value && filterControls.requested_by.get_value();
        val.bank_account = filterControls.bank_account && filterControls.bank_account.get_value && filterControls.bank_account.get_value();
        val.currency = filterControls.currency && filterControls.currency.get_value && filterControls.currency.get_value();
        val.approval_id = filterControls.approval_id && filterControls.approval_id.get_value && filterControls.approval_id.get_value();
        val.amount_min = filterControls.amount_min && filterControls.amount_min.get_value && filterControls.amount_min.get_value();
        val.amount_max = filterControls.amount_max && filterControls.amount_max.get_value && filterControls.amount_max.get_value();
        return val;
    }

    function clear_filters() {
        // Reset non-date filters to empty
        ['requested_by','bank_account','currency','approval_id','amount_min','amount_max']
            .forEach(fn => {
                const c = filterControls[fn];
                if (c && c.set_value) c.set_value('');
            });
        // Reset dates to defaults (3 months ago to today)
        set_default_dates();
    }

    $applyBtn.on('click', function () {
        paging.start = 0;
        fetch_rows(false);
    });
    $clearBtn.on('click', function () {
        clear_filters();
        paging.start = 0;
        fetch_rows(false);
    });

    function format_amount(value, currency) {
        try {
            return frappe.utils.format_currency(value || 0, currency || frappe.boot.sysdefaults.currency);
        } catch (e) {
            return value || 0;
        }
    }

    function render_rows(rows, append=false) {
        if (!append) {
            $tbody.empty();
        }
        const existing = $tbody.find('tr.data-row').length;
        if (!rows || !rows.length) {
            if (!append && existing === 0) {
                $tbody.append(`<tr><td colspan="9" class="text-muted text-center">No Payment Approval found</td></tr>`);
            }
            return;
        }

        rows.forEach((row, idx) => {
            const parentStripe = ((existing + idx) % 2 === 0) ? 'odd' : 'even';
            const posting_date = row.posting_date ? frappe.format(row.posting_date, { fieldtype: 'Date' }) : '';
            const posting_time = row.posting_time || row.time || '';
            const total_amount = format_amount(row.total_amount, row.currency);

            const $tr = $(`
                <tr class="cursor-pointer data-row ${parentStripe}">
                    <td>
                        <button class="btn btn-default btn-xs toggle-detail" title="Toggle details">▸</button>
                        <a class="doc-link">${frappe.utils.escape_html(row.name)}</a>
                    </td>
                    <td>${frappe.utils.escape_html(posting_date)}</td>
                    <td>${frappe.utils.escape_html(posting_time)}</td>
                    <td>${frappe.utils.escape_html(row.requested_by || '')}</td>
                    <td>${frappe.utils.escape_html(row.payment_type || row.Payment_type || '')}</td>
                    <td class="text-right">${total_amount}</td>
                    <td>${frappe.utils.escape_html(row.bank_account || row.back_account || '')}</td>
                    <td>${frappe.utils.escape_html(row.currency || '')}</td>
                    <td class="text-nowrap action-cell"><div class="action-wrapper"></div></td>
                </tr>
            `);

            // Detail row
            const $detailTr = $(`
                <tr class="detail-row belongs-${parentStripe}" style="display:none;">
                    <td colspan="9">
                        <div class="detail-body text-muted">Loading details...</div>
                    </td>
                </tr>
            `);

            $tr.data('detail-row', $detailTr);
            $tr.data('doc', null);
            $tr.data('detail-rendered', false);

            $tr.find('.doc-link').on('click', () => {
                frappe.set_route('Form', 'Payment Approval', row.name);
            });

            function get_invoices_rows(doc) {
                // Strictly use field `invoices` as requested
                if (Array.isArray(doc.invoices) && doc.invoices.length) {
                    return { key: 'invoices', rows: doc.invoices };
                }
                return { key: 'invoices', rows: [] };
            }

            function render_detail(doc) {
                const $body = $detailTr.find('.detail-body');
                if (!doc) {
                    $body.html(`<span class="text-muted">No details available</span>`);
                    return;
                }

                const batch = doc.batch_no || doc.batch_number || doc.batch || doc.batch_id || '';
                const { rows: transfers } = get_invoices_rows(doc);

                if (!transfers || !transfers.length) {
                    $body.html(`
                        <div class="mb-2"><strong>Batch No:</strong> ${frappe.utils.escape_html(batch || '-')}</div>
                        <div class="text-muted">No transfer rows</div>
                    `);
                    return;
                }

                const columns_fixed = [
                    { label: 'Invoice No', keys: ['invoice_no','invoice','reference_name','bill_no','reference'] },
                    { label: 'Supplier', keys: ['supplier','party_name','party'] },
                    { label: 'Supplier Bank No', keys: ['supplier_bank_no','bank_account_no','beneficiary_account_no','account_no','bank_account'] },
                    { label: 'Bank', keys: ['bank','bank_name','supplier_bank','beneficiary_bank'] },
                    { label: 'Amount', keys: ['amount','allocated_amount','base_amount','grand_total'] },
                    { label: 'Currency', keys: ['currency'] },
                ];

                function pick(row, keys) {
                    for (let k of keys) {
                        if (row[k] !== undefined && row[k] !== null && row[k] !== '') return row[k];
                    }
                    return '';
                }

                const thead = columns_fixed.map(c => `<th>${c.label}</th>`).join('');
                const rows_html = transfers.map(t => {
                    const tds = columns_fixed.map(c => {
                        let val = pick(t, c.keys);
                        if (c.label === 'Amount') {
                            val = format_amount(val, t['currency'] || doc.currency);
                        }
                        return `<td>${frappe.utils.escape_html(val != null ? String(val) : '')}</td>`;
                    }).join('');
                    return `<tr>${tds}</tr>`;
                }).join('');

                $body.html(`
                    <div class="mb-2"><strong>Batch No:</strong> ${frappe.utils.escape_html(batch || '-')}</div>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered detail-table">
                            <thead><tr>${thead}</tr></thead>
                            <tbody>${rows_html}</tbody>
                        </table>
                    </div>
                `);
                $tr.data('detail-rendered', true);
            }

            function toggle_detail(forceOpen) {
                const isVisible = $detailTr.is(':visible');
                const open = forceOpen !== undefined ? forceOpen : !isVisible;
                $detailTr.toggle(open);
                const $btn = $tr.find('.toggle-detail');
                $btn.text(open ? '▾' : '▸');
                const doc = $tr.data('doc');
                if (open && !$tr.data('detail-rendered')) {
                    render_detail(doc);
                }
            }

            $tr.on('click', '.toggle-detail', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggle_detail();
            });

            // Action buttons
            const $act = $tr.find('.action-cell .action-wrapper');
            const $btnApprove = $(`<button class="btn btn-sm btn-primary mr-2" style="display:none;">Approve</button>`);
            const $btnReject = $(`<button class="btn btn-sm btn-danger" style="display:none;">Reject</button>`);

            function apply(name, action) {
                // prevent row navigation
                page.set_indicator(__(`${action}...`), 'orange');
                $btnApprove.prop('disabled', true);
                $btnReject.prop('disabled', true);
                frappe.xcall('frappe.model.workflow.apply_workflow', {
                    doctype: 'Payment Approval',
                    docname: name,
                    action: action,
                }).then(() => {
                    frappe.show_alert({
                        message: __("{0} applied for {1}", [action, name]),
                        indicator: 'green',
                    });
                    reset_and_load();
                    $btnApprove.prop('disabled', false);
                    $btnReject.prop('disabled', false);
                    page.set_indicator(__('Loaded'), 'green');
                }).catch((err) => {
                    const msg = (err && err.message) || __('Failed to apply action');
                    frappe.msgprint({ title: __('Error'), indicator: 'red', message: msg });
                    $btnApprove.prop('disabled', false);
                    $btnReject.prop('disabled', false);
                    page.set_indicator(__('Loaded'), 'green');
                });
            }

            $btnApprove.on('click', (e) => { e.stopPropagation(); apply(row.name, 'Approve'); });
            $btnReject.on('click', (e) => { e.stopPropagation(); apply(row.name, 'Reject'); });

            $act.append($btnApprove, $btnReject);

            // Use transitions and doc provided by server
            const actions = Array.isArray(row.transitions) ? row.transitions : [];
            $tr.data('doc', row.doc || null);
            if (actions.includes('Approve')) $btnApprove.show();
            if (actions.includes('Reject')) $btnReject.show();
            if (!actions.length) {
                $act.append(`<span class="text-muted">No actions</span>`);
            }
            if (showAll) {
                render_detail(row.doc || null);
                toggle_detail(true);
            }

            $tbody.append($tr, $detailTr);
        });
    }

    // Global show-all toggle
    $showAll.on('change', function () {
        showAll = !!$(this).prop('checked');
        // Use the row's own toggle logic to ensure rendering happens
        $tbody.find('tr').each(function () {
            const $row = $(this);
            if (!$row.data) return;
            const $detail = $row.data('detail-row');
            if ($detail) {
                const isVisible = $detail.is(':visible');
                if (showAll && !isVisible) {
                    $row.find('.toggle-detail').trigger('click');
                } else if (!showAll && isVisible) {
                    $row.find('.toggle-detail').trigger('click');
                }
            }
        });
    });

    function update_load_more(has_more) {
        paging.has_more = !!has_more;
        $loadMore.toggle(paging.has_more);
        const displayed = $tbody.find('tr.data-row').length;
        const total = paging.total || 0;
        if (total > 0) {
            $count.text(`${displayed} of ${total}`);
            $count.show();
        } else {
            $count.hide();
        }
    }

    function fetch_rows(append=false) {
        if (paging.loading) return;
        paging.loading = true;
        page.set_indicator(__('Loading'), 'orange');
        const filters = get_filters_payload();
        return frappe.call({
            method: 'erpnext.uob.page.payment_bulk_approval.payment_bulk_approval.get_data',
            args: { start: paging.start, page_length: paging.page_length, filters },
        }).then((r) => {
            const payload = r && r.message ? r.message : {};
            const rows = payload.results || [];
            render_rows(rows, append);
            paging.start = payload.next_start || (paging.start + rows.length);
            paging.total = payload.total || paging.total;
            update_load_more(payload.has_more);
            page.set_indicator(__('Loaded'), 'green');
            paging.loading = false;
        }).catch(() => {
            if (!append) render_rows([]);
            update_load_more(false);
            page.set_indicator(__('Failed'), 'red');
            paging.loading = false;
        });
    }

    function reset_and_load() {
        paging.start = 0;
        return fetch_rows(false);
    }

    $loadMore.on('click', function () {
        fetch_rows(true);
    });

    // initial load - first 20
    reset_and_load();
};
