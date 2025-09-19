frappe.pages['payment-bulk-approval'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Payment Bulk Approval',
        single_column: true,
    });

    // Back to native List view (desktop)
    page.set_secondary_action(__('Back to Payment Approval'), function () {
        frappe.set_route('List', 'Payment Approval');
    });

    // Reload action (top-right) (desktop)
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
                .payment-bulk-approval tr.data-row.processing td { opacity: 0.6; }
                /* Collapsible detail styling tied to parent row */
                .payment-bulk-approval tr.detail-row.belongs-odd td { background: #fff7e6; border-left: 4px solid #fff1d8; }
                .payment-bulk-approval tr.detail-row.belongs-even td { background: #ffe9d1; border-left: 4px solid #ffddb4; }
                .payment-bulk-approval tr.mobile-actions-row.belongs-odd td { background: #fff7e6; border-left: 4px solid #fff1d8; }
                .payment-bulk-approval tr.mobile-actions-row.belongs-even td { background: #ffe9d1; border-left: 4px solid #ffddb4; }
                .payment-bulk-approval .detail-body { padding: 8px 12px; }
                .payment-bulk-approval .detail-table { width: 100%; table-layout: auto; }
                .payment-bulk-approval .detail-desktop { display: block; }
                .payment-bulk-approval .detail-mobile { display: none; }
                .payment-bulk-approval tr.mobile-actions-row { display: none; }
                .payment-bulk-approval .mobile-actions { display: none; justify-content: flex-end; gap: 8px; }
                .payment-bulk-approval .controls { display: flex; align-items: center; gap: 16px; }
                .payment-bulk-approval .filter-bar { margin-top: 8px; }
                .payment-bulk-approval .filters-grid { display: grid; grid-template-columns: repeat(3, minmax(220px, 1fr)); gap: 8px 16px; }
                .payment-bulk-approval .filters-advanced { display: contents; }
                .payment-bulk-approval .filters-toggle { display: none; }
                .payment-bulk-approval .filters-actions { display:flex; gap: 8px; margin-top: 8px; }
                .payment-bulk-approval .list-footer { display:flex; justify-content:center; align-items:center; padding: 8px; position: relative; }
                .payment-bulk-approval .btn-load-more { min-width: 160px; }
                .payment-bulk-approval .list-count { position: absolute; right: 8px; color: var(--text-muted); font-size: 12px; }

                /* Mobile toolbar and responsive tweaks */
                .payment-bulk-approval .mobile-toolbar { display: none; justify-content: flex-end; align-items: center; margin-bottom: 8px; }
                .payment-bulk-approval .kebab { border: none; background: transparent; font-size: 20px; line-height: 1; padding: 6px 8px; cursor: pointer; }
                .payment-bulk-approval .kebab-menu { position: absolute; right: 0; top: 100%; background: var(--bg-color) ; border: 1px solid var(--border-color); border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); min-width: 180px; display: none; z-index: 10; }
                .payment-bulk-approval .kebab-wrap { position: relative; }
                .payment-bulk-approval .kebab-menu .item { display: block; width: 100%; padding: 8px 12px; background: transparent; border: none; text-align: left; cursor: pointer; }
                .payment-bulk-approval .kebab-menu .item:hover { background: var(--bg-light); }
                .payment-bulk-approval .mobile-only-currency { display: none; }
                .payment-bulk-approval .list-table-wrapper { overflow: visible; }

                @media (max-width: 768px) {
                    .payment-bulk-approval .detail-body { padding: 6px 0px; }
                    .payment-bulk-approval tr.detail-row.belongs-even td { padding-bottom: 2px; }
                    .payment-bulk-approval tr.mobile-actions-row.belongs-even td { padding-botton: 16px }

                    /* Hide page header action buttons on mobile */
                    .page-actions .btn { display: none !important; }
                    .payment-bulk-approval .mobile-toolbar { display: flex; }

                    /* Stack filters and hide advanced by default */
                    .payment-bulk-approval .filters-grid { grid-template-columns: 1fr; }
                    .payment-bulk-approval .filters-toggle { display: inline-flex; align-items: center; gap: 6px; margin-bottom: 6px; }
                    .payment-bulk-approval .filters-advanced.collapse { display: none; }

                    /* Controls vertical alignment */
                    .payment-bulk-approval .controls { flex-wrap: wrap; gap: 8px; }
                    .payment-bulk-approval .controls .ml-auto { margin-left: 0 !important; }

                    /* Table: keep only key columns */
                    .payment-bulk-approval th.col-posting-date,
                    .payment-bulk-approval td.col-posting-date,
                    .payment-bulk-approval th.col-requested-by,
                    .payment-bulk-approval td.col-requested-by,
                    .payment-bulk-approval th.col-type,
                    .payment-bulk-approval td.col-type,
                    .payment-bulk-approval th.col-currency,
                    .payment-bulk-approval td.col-currency,
                    .payment-bulk-approval th.col-bank,
                    .payment-bulk-approval td.col-bank { display: none; }

                    /* Let visible columns fill full width */
                    .payment-bulk-approval table { table-layout: auto; }
                    .payment-bulk-approval th, .payment-bulk-approval td { width: auto !important; }
                    .payment-bulk-approval th.col-name, .payment-bulk-approval td.col-name { width: 100% !important; white-space: normal; }
                    .payment-bulk-approval th.col-amount, .payment-bulk-approval td.col-amount { width: 30% !important; }
                    .payment-bulk-approval th.col-action, .payment-bulk-approval td.col-action { width: 20% !important; }

                    /* Tighter actions */
                    .payment-bulk-approval .action-cell .action-wrapper { gap: 6px; justify-content: flex-end; }

                    /* Show currency next to amount on mobile */
                    .payment-bulk-approval .mobile-only-currency { display: inline; color: var(--text-muted); margin-left: 4px; }

                    /* Allow horizontal scroll if needed */
                    .payment-bulk-approval .list-table-wrapper { overflow-x: auto; }

                    /* Name cell: place toggle after doc-link and tidy spacing */
                    .payment-bulk-approval td.col-name { display: flex; align-items: center; }
                    .payment-bulk-approval td.col-name .doc-link { order: 1; }
                    .payment-bulk-approval td.col-name .toggle-detail { order: 1; margin-left: 0px; margin-right: 8px; padding: 2px 6px; border: none; background: white; }

                    /* Use separate mobile actions row */
                    .payment-bulk-approval th.col-action, .payment-bulk-approval td.col-action { display: none; }
                    .payment-bulk-approval tr.mobile-actions-row { display: table-row; }
                    .payment-bulk-approval .mobile-actions { display: flex; }

                    /* Detail rows as stacked cards on mobile */
                    .payment-bulk-approval .detail-desktop { display: none; }
                    .payment-bulk-approval .detail-mobile { display: block; }
                    .payment-bulk-approval .detail-mobile .detail-mobile-list { display: grid; gap: 8px; }
                    .payment-bulk-approval .detail-mobile .detail-item { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 6px; padding: 8px 10px; }
                    .payment-bulk-approval .detail-mobile .item-head { display: flex; align-items: center; gap: 8px; justify-content: space-between; flex-wrap: wrap; }
                    .payment-bulk-approval .detail-mobile .item-head .left { display: flex; align-items: center; gap: 8px; }
                    .payment-bulk-approval .detail-mobile .item-amount { font-weight: 600; }
                    .payment-bulk-approval .detail-mobile .item-line { font-size: 12px; color: var(--text-muted); }
                    .payment-bulk-approval .detail-mobile .item-line .k { color: var(--text-color); font-weight: 500; margin-right: 4px; }
                }
            </style>
            <div class="mb-2 mobile-toolbar">
                <div class="kebab-wrap">
                    <button class="kebab" title="More">⋮</button>
                    <div class="kebab-menu">
                        <button class="item act-reload">Reload</button>
                        <button class="item act-back">Back to Payment Approval</button>
                    </div>
                </div>
            </div>
            <div class="mb-4">
                <div class="filter-bar">
                    <button class="btn btn-sm btn-default filters-toggle"><span class="toggle-label">Show more filters</span></button>
                    <div class="filters-grid">
                        <div class="filters-primary"></div>
                        <div class="filters-advanced"></div>
                    </div>
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
                    <label class="ml-auto mb-0 text-muted mr-3" style="font-size: 1.1em;">
                        <div>Payment Amount: <b class="pending-amount">$0</b></div>
                    </label>
                </div>
            </div>
            <div class="frappe-card">
                <div class="frappe-card-body" style="padding: 0;">
                    <div class="list-table-wrapper">
                        <table class="table table-bordered table-hover">
                            <thead>
                                <tr>
                                    <th class="col-name" style="width: 12.9%;">Name</th>
                                    <th class="col-posting-date" style="width: 15.06%;">Posting Date</th>
                                    <th class="col-requested-by" style="width: 10.33%;">Requested By</th>
                                    <th class="col-type" style="width: 6.88%;">Type</th>
                                    <th class="col-amount text-right" style="width: 10.76%;">T. Amount</th>
                                    <th class="col-currency" style="width: 6.02%;">Cry</th>
                                    <th class="col-bank" style="width: 23.24%;">Bank Account</th>
                                    <th class="col-action text-center" style="width: 14.82%;">Action</th>
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
    const $filtersPrimary = $container.find('.filters-primary');
    const $filtersAdvanced = $container.find('.filters-advanced');
    const $filtersToggle = $container.find('.filters-toggle');
    const $kebab = $container.find('.kebab');
    const $kebabMenu = $container.find('.kebab-menu');
    const $kebabReload = $container.find('.kebab-menu .act-reload');
    const $kebabBack = $container.find('.kebab-menu .act-back');
    const $applyBtn = $container.find('.apply-filters');
    const $clearBtn = $container.find('.clear-filters');
    const $pendingAmount = $container.find('.pending-amount');
    let showAll = false;
    const paging = { start: 0, page_length: 20, has_more: false, loading: false };
    const filterControls = {};
    let pendingTotal = 0;
    let pendingCurrency = null;

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
    const primaryFilterKeys = ['posting_date_from', 'posting_date_to', 'requested_by'];
    filterDefs.forEach(def => {
        const isPrimary = primaryFilterKeys.includes(def.fieldname);
        const $wrap = $('<div></div>').appendTo(isPrimary ? $filtersPrimary : $filtersAdvanced);
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

    // Mobile: advanced filters collapsed by default
    function isSmallScreen() { return false }
    function setFiltersCollapsed(collapsed) {
        if (collapsed) {
            $filtersAdvanced.addClass('collapse');
            $filtersToggle.find('.toggle-label').text(__('Show more filters'));
        } else {
            $filtersAdvanced.removeClass('collapse');
            $filtersToggle.find('.toggle-label').text(__('Hide filters'));
        }
    }
    setFiltersCollapsed(isSmallScreen());
    $filtersToggle.on('click', function() {
        const willCollapse = !$filtersAdvanced.hasClass('collapse');
        setFiltersCollapsed(willCollapse);
    });

    // Mobile kebab menu actions
    $kebab.on('click', function(e) {
        e.stopPropagation();
        $kebabMenu.toggle();
    });
    $(document).on('click', function() { $kebabMenu.hide(); });
    $kebabReload.on('click', function() { $kebabMenu.hide(); if (paging && paging.loading) return; reset_and_load(); });
    $kebabBack.on('click', function() { $kebabMenu.hide(); frappe.set_route('List', 'Payment Approval'); });

    // Keep name-cell button/link order consistent across breakpoints
    function reorder_name_cell($tr) {
        try {
            const small = isSmallScreen();
            const $nameCell = $tr.find('td.col-name');
            const $btnTgl = $nameCell.find('.toggle-detail').first();
            const $docLink = $nameCell.find('.doc-link').first();
            if (!$btnTgl.length || !$docLink.length) return;
            if (small) {
                if ($docLink.next()[0] !== $btnTgl[0]) $docLink.after($btnTgl);
            } else {
                if ($btnTgl.next()[0] !== $docLink[0]) $docLink.before($btnTgl);
            }
        } catch (e) {}
    }
    function reorder_all_rows() {
        $tbody.find('tr.data-row').each(function() { reorder_name_cell($(this)); });
    }
    $(window).on('resize', function () { reorder_all_rows(); });

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
       return fmt_money(value, currency=currency)
    }

    // (Reverted) Use default frappe currency formatter

    // Safe URL builder for opening forms in new tab
    function url_to_form(doctype, name) {
        try {
            const slug = String(doctype || '')
                .trim()
                .toLowerCase()
                .replace(/\s+/g, '-');
            return `/app/${slug}/${encodeURIComponent(String(name || ''))}`;
        } catch (e) {
            return `#Form/${doctype}/${name}`;
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
            const approval_url = url_to_form('Payment Approval', row.name);

            const $tr = $(`
                <tr class="cursor-pointer data-row ${parentStripe}">
                    <td class="col-name">
                        <button class="btn btn-default btn-xs toggle-detail" title="Toggle details">></button>
                        <a class="doc-link" href="${approval_url}" target="_blank" rel="noopener">${frappe.utils.escape_html(row.name)}</a>
                    </td>
                    <td class="col-posting-date">${frappe.utils.escape_html(posting_date)} ${frappe.utils.escape_html(posting_time)}</td>
                    <td class="col-requested-by">${frappe.utils.escape_html(row.requested_by || '')}</td>
                    <td class="col-type">${frappe.utils.escape_html(row.payment_type || row.Payment_type || '')}</td>
                    <td class="col-amount text-right">${total_amount}<span class="mobile-only-currency"> ${frappe.utils.escape_html(row.currency || '')}</span></td>
                    <td class="col-currency">${frappe.utils.escape_html(row.currency || '')}</td>
                    <td class="col-bank">${frappe.utils.escape_html(row.bank_account || row.back_account || '')}</td>
                    <td class="col-action text-nowrap action-cell" style="width: 14.82%;"><div class="action-wrapper"></div></td>
                </tr>
            `);
            // Ensure correct order per screen size
            reorder_name_cell($tr);

            // Mobile-only actions row (shown only on small screens via CSS)
            const $mobileActionsTr = $(`
                <tr class="mobile-actions-row belongs-${parentStripe}">
                    <td colspan="9">
                        <div class="action-wrapper mobile-actions"></div>
                    </td>
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
            $tr.data('mobile-actions-row', $mobileActionsTr);
            $tr.data('doc', null);
            $tr.data('detail-rendered', false);

            // Link opens Payment Approval in new tab via anchor href

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
                    { label: 'Select', keys: ['__select__'] },
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

                // Build mobile stacked list HTML (always render; CSS toggles visibility)
                const mobile_items_html = transfers.map(t => {
                        const link_name = t.invoice || t.reference_name || t.invoice_no || '';
                        const href = link_name ? url_to_form('Purchase Invoice', link_name) : '';
                        const supplier = pick(t, ['supplier','party_name','party']);
                        const accNo = t.bank_account_no || t.supplier_bank_no || t.beneficiary_account_no || t.account_no || t.bank_account || '';
                        const accName = t.bank_account_name || '';
                        const bank_acc = accNo && accName ? `${accNo} - ${accName}` : (accNo || accName || '');
                        const bank = pick(t, ['bank','bank_name','supplier_bank','beneficiary_bank']);
                        const amount_raw = pick(t, ['amount','allocated_amount','base_amount','grand_total']);
                        const amount = format_amount(amount_raw, t['currency'] || doc.currency);
                        const currency = t['currency'] || doc.currency || '';
                        const disabled = link_name ? '' : ' disabled';
                        const checked = link_name ? ' checked' : '';
                        const link_html = link_name ? `<a href="${href}" target="_blank" rel="noopener">${frappe.utils.escape_html(link_name)}</a>` : `<span>${frappe.utils.escape_html(link_name || '-')}</span>`;
                        return `
                            <div class="detail-item">
                                <div class="item-head">
                                    <div class="left">
                                        <input type="checkbox" class="invoice-select" data-invoice-name="${frappe.utils.escape_html(link_name)}"${disabled}${checked}>
                                        ${link_html}
                                    </div>
                                    <div class="item-amount">${frappe.utils.escape_html(amount)} ${frappe.utils.escape_html(currency)}</div>
                                </div>
                                <div class="item-line"><span class="k">Supplier:</span> <span class="v">${frappe.utils.escape_html(supplier || '-')}</span></div>
                                <div class="item-line"><span class="k">Bank Acc:</span> <span class="v">${frappe.utils.escape_html(bank_acc || '-')}</span></div>
                                <div class="item-line"><span class="k">Bank:</span> <span class="v">${frappe.utils.escape_html(bank || '-')}</span></div>
                            </div>
                        `;
                    }).join('');
                const mobile_html = `
                    <div class="detail-mobile">
                        <div class="mb-2"><strong>Batch No:</strong> ${frappe.utils.escape_html(batch || '-')}</div>
                        <label class="mb-2 d-flex align-items-center"><input type="checkbox" class="invoice-select-all" checked style="margin-right: 8px;"> <span>Select all</span></label>
                        <div class="detail-mobile-list">${mobile_items_html}</div>
                    </div>
                `;

                const thead = columns_fixed.map(c => {
                    if (c.label === 'Select') {
                        return `<th class=\"text-center\" style=\"width: 40px;\"><input type=\"checkbox\" class=\"invoice-select-all\" title=\"Select all\" checked></th>`;
                    }
                    return `<th${c.label === 'Amount' ? ' class=\"text-right\"' : ''}>${c.label}</th>`;
                }).join('');
                const rows_html = transfers.map(t => {
                    const tds = columns_fixed.map(c => {
                        let val = pick(t, c.keys);
                        if (c.label === 'Select') {
                            // Use best-effort invoice identifier found in row
                            const link_name = t.invoice || t.reference_name || t.invoice_no || '';
                            const disabled = link_name ? '' : ' disabled';
                            // Default checked (user can uncheck unwanted rows)
                            const checked = link_name ? ' checked' : '';
                            return `<td class=\"text-center\"><input type=\"checkbox\" class=\"invoice-select\" data-invoice-name=\"${frappe.utils.escape_html(link_name)}\"${disabled}${checked}></td>`;
                        }
                        if (c.label === 'Amount') {
                            val = format_amount(val, t['currency'] || doc.currency);
                            return `<td class=\"text-right\">${frappe.utils.escape_html(val != null ? String(val) : '')}</td>`;
                        } else if (c.label === 'Supplier Bank No') {
                            const accNo = t.bank_account_no || t.supplier_bank_no || t.beneficiary_account_no || t.account_no || t.bank_account || '';
                            const accName = t.bank_account_name || '';
                            if (accNo && accName) {
                                val = `${accNo} - ${accName}`;
                            } else if (accNo) {
                                val = accNo;
                            } else if (accName) {
                                val = accName;
                            }
                        } else if (c.label === 'Invoice No') {
                            const link_name = t.invoice || t.reference_name || t.invoice_no || '';
                            if (link_name) {
                                const href = url_to_form('Purchase Invoice', link_name);
                                const label = frappe.utils.escape_html(val != null ? String(val) : '');
                                return `<td><a href="${href}" target="_blank" rel="noopener">${label}</a></td>`;
                            }
                        }
                        return `<td>${frappe.utils.escape_html(val != null ? String(val) : '')}</td>`;
                    }).join('');
                    return `<tr>${tds}</tr>`;
                }).join('');

                $body.html(`
                    <div class="detail-desktop">
                        <div class="mb-2"><strong>Batch No:</strong> ${frappe.utils.escape_html(batch || '-')}</div>
                        <div class="table-responsive">
                            <table class="table table-sm table-bordered detail-table">
                                <thead><tr>${thead}</tr></thead>
                                <tbody>${rows_html}</tbody>
                            </table>
                        </div>
                    </div>
                `);
                $body.append(mobile_html);
                // Hook up select-all for this detail table
                const $table = $body.find('table.detail-table');
                $table.on('change', '.invoice-select-all', function() {
                    const checked = $(this).is(':checked');
                    $table.find('tbody .invoice-select').prop('checked', checked);
                });
                // Default: all selected on initial render
                $table.find('.invoice-select-all').prop('checked', true).trigger('change');
                // Hook mobile select-all
                const $wrap = $body.find('.detail-mobile');
                $wrap.on('change', '.invoice-select-all', function() {
                    const checked = $(this).is(':checked');
                    $wrap.find('.invoice-select').prop('checked', checked);
                });
                $wrap.find('.invoice-select-all').prop('checked', true).trigger('change');
                $tr.data('detail-rendered', true);
            }

            function toggle_detail(forceOpen) {
                const isVisible = $detailTr.is(':visible');
                const open = forceOpen !== undefined ? forceOpen : !isVisible;
                $detailTr.toggle(open);
                const $btn = $tr.find('.toggle-detail');
                $btn.text(open ? 'v' : '>');
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
            const $actMobile = $mobileActionsTr.find('.action-wrapper');
            const $btnApprove = $(`<button class="btn btn-sm btn-primary mr-2" style="display:none; min-width: 72px;">Approve</button>`);
            const $btnReject = $(`<button class="btn btn-sm btn-danger" style="display:none; min-width: 72px;">Reject</button>`);
            const $btnApproveM = $(`<button class="btn btn-sm btn-primary mr-2" style="display:none; min-width: 72px;">Approve</button>`);
            const $btnRejectM = $(`<button class="btn btn-sm btn-danger" style="display:none; min-width: 72px;">Reject</button>`);

            function apply(name, action) {
                // prevent row navigation
                page.set_indicator(__(`${action}...`), 'orange');
                [$btnApprove, $btnApproveM].forEach($b => $b.prop('disabled', true));
                [$btnReject, $btnRejectM].forEach($b => $b.prop('disabled', true));
                const originalApproveText = $btnApprove.text() || 'Approve';
                const originalRejectText = $btnReject.text() || 'Reject';
                if (action === 'Approve') {
                    $tr.addClass('processing');
                    [$btnApprove, $btnApproveM].forEach($b => $b.text(__('Approving...')));
                } else if (action === 'Reject') {
                    [$btnReject, $btnRejectM].forEach($b => $b.text(__('Rejecting...')));
                }
                // Collect selected invoices (if any) from this row's detail table
                const $detail = $tr.data('detail-row');
                let selected_invoices = [];
                if ($detail && $detail.length) {
                    selected_invoices = $detail.find('.invoice-select:checked')
                        .map(function() { return $(this).data('invoice-name'); })
                        .get()
                        .filter(x => !!x);
                    selected_invoices = Array.from(new Set(selected_invoices));
                }

                frappe.xcall('erpnext.uob.page.payment_bulk_approval.payment_bulk_approval.get_apply_workflow', {
                    docname: name,
                    action: action,
                    selected_invoices: selected_invoices,
                }).then(() => {
                    frappe.show_alert({
                        message: __("{0} applied for {1}", [action, name]),
                        indicator: 'green',
                    });
                    if (action === 'Approve') {
                        if ($detail) $detail.remove();
                        const $mobileAct = $tr.data('mobile-actions-row');
                        if ($mobileAct) $mobileAct.remove();
                        $tr.remove();
                        if (typeof paging.total === 'number') paging.total = Math.max(0, paging.total - 1);
                        recalc_stripes();
                        const displayed = $tbody.find('tr.data-row').length;
                        const has_more = (paging.total || 0) > displayed;
                        update_load_more(has_more);
                        // Auto-fill the gap with next record if available
                        if (has_more) {
                            fetch_next_one();
                        } else {
                            const amt = Number(row.total_amount || 0);
                            set_pending_label(Math.max(0, (pendingTotal || 0) - amt), pendingCurrency);
                        }
                    } else {
                        reset_and_load();
                    }
                    [$btnApprove, $btnApproveM].forEach($b => $b.prop('disabled', false).text(originalApproveText));
                    [$btnReject, $btnRejectM].forEach($b => $b.prop('disabled', false).text(originalRejectText));
                    page.set_indicator(__('Loaded'), 'green');
                }).catch((err) => {
                    const msg = (err && err.message) || __('Failed to apply action');
                    frappe.msgprint({ title: __('Error'), indicator: 'red', message: msg });
                    $tr.removeClass('processing');
                    [$btnApprove, $btnApproveM].forEach($b => $b.prop('disabled', false).text(originalApproveText));
                    [$btnReject, $btnRejectM].forEach($b => $b.prop('disabled', false).text(originalRejectText));
                    page.set_indicator(__('Loaded'), 'green');
                });
            }

            $btnApprove.on('click', (e) => { e.stopPropagation(); apply(row.name, 'Approve'); });
            $btnReject.on('click', (e) => { e.stopPropagation(); apply(row.name, 'Reject'); });
            $btnApproveM.on('click', (e) => { e.stopPropagation(); apply(row.name, 'Approve'); });
            $btnRejectM.on('click', (e) => { e.stopPropagation(); apply(row.name, 'Reject'); });

            $act.append($btnApprove, $btnReject);
            $actMobile.append($btnApproveM, $btnRejectM);

            // Use transitions and doc provided by server
            const actions = Array.isArray(row.transitions) ? row.transitions : [];
            $tr.data('doc', row.doc || null);
            if (actions.includes('Approve')) { $btnApprove.show(); $btnApproveM.show(); }
            if (actions.includes('Reject')) { $btnReject.show(); $btnRejectM.show(); }
            if (!actions.length) {
                $act.append(`<span class="text-muted">No actions</span>`);
                $actMobile.append(`<span class="text-muted">No actions</span>`);
            }
            if (showAll) {
                render_detail(row.doc || null);
                toggle_detail(true);
            }

            // Order for mobile UX: data row -> detail row (collapsible) -> mobile actions row (fixed at bottom)
            $tbody.append($tr, $detailTr, $mobileActionsTr);
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

    function set_pending_label(total, currency) {
        pendingTotal = Number(total || 0);
        pendingCurrency = currency || null;
        $pendingAmount.text(format_amount(pendingTotal, pendingCurrency));
    }

    function recalc_stripes() {
        $tbody.find('tr.data-row').each(function (i) {
            const $row = $(this);
            const stripe = (i % 2 === 0) ? 'odd' : 'even';
            $row.removeClass('odd even').addClass(stripe);
            const $detail = $row.data && $row.data('detail-row');
            if ($detail) {
                $detail.removeClass('belongs-odd belongs-even').addClass('belongs-' + stripe);
            }
            const $mob = $row.data && $row.data('mobile-actions-row');
            if ($mob) {
                $mob.removeClass('belongs-odd belongs-even').addClass('belongs-' + stripe);
            }
        });
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
            if (typeof payload.pending_total === 'number') {
                set_pending_label(payload.pending_total, payload.pending_currency);
            }
            page.set_indicator(__('Loaded'), 'green');
            paging.loading = false;
        }).catch(() => {
            if (!append) render_rows([]);
            update_load_more(false);
            page.set_indicator(__('Failed'), 'red');
            paging.loading = false;
        });
    }

    // fetch exactly one more row to keep list filled after removal
    function fetch_next_one() {
        if (paging.loading) return Promise.resolve();
        paging.loading = true;
        const filters = get_filters_payload();
        return frappe.call({
            method: 'erpnext.uob.page.payment_bulk_approval.payment_bulk_approval.get_data',
            args: { start: paging.start, page_length: 1, filters },
        }).then((r) => {
            const payload = r && r.message ? r.message : {};
            const rows = payload.results || [];
            if (rows.length) {
                render_rows(rows, true);
            }
            paging.start = payload.next_start || (paging.start + rows.length);
            paging.total = payload.total || paging.total;
            update_load_more(payload.has_more);
            if (typeof payload.pending_total === 'number') {
                set_pending_label(payload.pending_total, payload.pending_currency);
            }
            paging.loading = false;
        }).catch(() => {
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
