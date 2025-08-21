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
            </style>
            <div class="mb-4">
                <div class="controls">
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
                    </div>
                </div>
            </div>
        </div>
    `);

    $(page.body).empty().append($container);

    const $tbody = $container.find('tbody');
    const $showAll = $container.find('.show-all-details');
    let showAll = false;

    function format_amount(value, currency) {
        try {
            return frappe.utils.format_currency(value || 0, currency || frappe.boot.sysdefaults.currency);
        } catch (e) {
            return value || 0;
        }
    }

    function render_rows(rows) {
        $tbody.empty();
        if (!rows || !rows.length) {
            $tbody.append(
                `<tr><td colspan="9" class="text-muted text-center">No Payment Approval found</td></tr>`
            );
            return;
        }

        rows.forEach((row, idx) => {
            const parentStripe = (idx % 2 === 0) ? 'odd' : 'even';
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
                    load_rows();
                }).catch((err) => {
                    const msg = (err && err.message) || __('Failed to apply action');
                    frappe.msgprint({ title: __('Error'), indicator: 'red', message: msg });
                }).finally(() => {
                    $btnApprove.prop('disabled', false);
                    $btnReject.prop('disabled', false);
                    page.set_indicator(__('Loaded'), 'green');
                });
            }

            $btnApprove.on('click', (e) => { e.stopPropagation(); apply(row.name, 'Approve'); });
            $btnReject.on('click', (e) => { e.stopPropagation(); apply(row.name, 'Reject'); });

            $act.append($btnApprove, $btnReject);

            // Determine available workflow actions for this document and cache doc for details
            (function resolve_actions() {
                // show a lightweight placeholder while loading
                const $loading = $(`<span class="text-muted">Loading...</span>`);
                $act.append($loading);

                frappe.xcall('frappe.client.get', {
                    doctype: 'Payment Approval',
                    name: row.name,
                }).then((doc) => {
                    $tr.data('doc', doc);
                    // render detail if needed (either global showAll or row already expanded)
                    if (showAll || $detailTr.is(':visible')) {
                        render_detail(doc);
                        if (!$detailTr.is(':visible')) toggle_detail(true);
                    }
                    return frappe.xcall('frappe.model.workflow.get_transitions', { doc });
                }).then((transitions) => {
                    const actions = (transitions || []).map(t => t.action);
                    if (actions.includes('Approve')) $btnApprove.show();
                    if (actions.includes('Reject')) $btnReject.show();
                    if (!actions.length) {
                        $act.append(`<span class="text-muted">No actions</span>`);
                    }
                }).catch(() => {
                    $act.append(`<span class="text-danger">Workflow unavailable</span>`);
                }).finally(() => {
                    $loading.remove();
                });
            })();

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

    function load_rows() {
        page.set_indicator(__('Loading'), 'orange');
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Payment Approval',
                fields: [
                    'name',
                    'posting_date',
                    'time',
                    'requested_by',
                    'payment_type',
                    'total_amount',
                    'bank_account',
                    'currency',
                ],
                limit_page_length: 50,
                order_by: 'modified desc',
            },
        }).then((r) => {
            render_rows(r && r.message ? r.message : []);
            page.set_indicator(__('Loaded'), 'green');
        }).catch(() => {
            render_rows([]);
            page.set_indicator(__('Failed'), 'red');
        });
    }

    // initial load
    load_rows();
};
