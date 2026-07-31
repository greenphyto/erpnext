# Hooks & Customization

## Summary
Custom hooks, doc_events, override methods, and scheduled tasks registered in `hooks.py` for GP ERPNext. Includes global validation hooks, naming series overrides, AI agent integration, FOMS sync triggers, custom email handling, MinIO backup, scrap entry automation, and PDF page numbering.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 5681156aa1 | feat(hooks): add AI Agent Memory auto-update on PI submit | 2026-07-03 |
| fa6b154543 | always use custom date in AI | 2026-01-09 |
| 45124ab187 | set posting date equal to custom date | 2026-01-05 |
| 493226335f | submit directly scrap entry and custom account | 2025-12-08 |
| bc772b0d09 | add to hooks | 2025-10-27 |
| d32a50ecac | add to hooks | 2025-09-26 |
| 5b3d1190f1 | add custom bucket and folder | 2025-08-07 |
| 3a0114130c | check custom and promise the actions | 2025-08-01 |
| f80c604921 | move custom AI field to customize form | 2025-07-31 |
| c1d2257375 | allow custom file path | 2025-05-26 |
| 4efaccc1a5 | add custom footer | 2024-12-13 |
| 7440e08916 | move trigger to hooks | 2024-08-30 |
| 1fd78a7867 | add to hooks | 2024-05-20 |
| 919fe2404b | add custom validate purchase user | 2024-02-28 |
| 705968f541 | resgiter to hooks | 2024-01-24 |

## Affected Files
**Hooks Configuration:**
- erpnext/hooks.py

**AI Agent:**
- erpnext/ai_agent/custom/buying_settings.json
- erpnext/ai_agent/custom/purchase_invoice.json
- erpnext/ai_agent/doctype/email_invoice/email_invoice.py

**Controllers:**
- erpnext/controllers/erp.py
- erpnext/buying/doctype/supplier/supplier.py
- erpnext/selling/doctype/customer/customer.py

**FOMS/Backup:**
- erpnext/foms/doctype/minio_backup_settings/minio_backup_settings.json
- erpnext/foms/doctype/minio_backup_settings/minio_backup_settings.py
- erpnext/foms/doctype/payment_approval/payment_approval.py

**Doctype Customizations:**
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.json
- erpnext/buying/doctype/buying_settings/buying_settings.json
- erpnext/stock/doctype/delivery_note/delivery_note.js
- erpnext/stock/doctype/material_request/material_request.py
- erpnext/stock/doctype/scrap_items/scrap_items.json
- erpnext/stock/doctype/scrap_request/scrap_request.py

## Flow/Logic

### Global Doc Events (`doc_events["*"]`)
1. **validate**: `validate_company_selected` - ensures the user's session company matches the document's company. Prevents cross-company data entry errors.
2. **before_naming**: `change_naming_series` - dynamically adjusts naming series based on company context, allowing multi-company setups to have distinct document numbering.

### Purchase Invoice Hooks
1. **on_submit**:
   - `change_temporary_invoice`: AI Agent converts temporary invoice references to permanent ones.
   - `update_memory_on_submit`: Updates AI Agent Memory with submitted PI data for learning/matching.
2. **onload**: `setup_onload` - prepares AI agent-related UI elements when PI form loads.

### Sales Invoice Hooks
1. **on_submit**: Includes `billing_consignment_controller` for consignment billing automation.
2. **on_cancel**: Same controller handles reversal logic.

### Stock Entry Hooks
1. **on_submit**:
   - `sync_log`: Syncs stock entry to FOMS.
   - `detect_salad_items`: Identifies salad product stock entries for special handling.
   - `check_missing_se_rate`: Validates that all stock entry items have rates.
   - `create_sample_after_work_order`: Auto-creates sample entries after production.
   - `detect_work_order_different`: Flags qty differences between work order and actual production.
   - `update_completed_and_requested_qty`: Updates Material Request fulfillment status.
   - `create_prod_variance_entry`: Creates production variance records.
   - `stock_entry_controller`: Consignment request handling.
2. **before_cancel**: Reversal checks for salad items and repack stock entries.

### FOMS Sync Triggers
Multiple doctypes have `on_submit`/`on_cancel`/`on_update` hooks pointing to `erpnext.controllers.foms.sync_log`:
- Supplier, Customer, Warehouse, Stock Reconciliation, Purchase Receipt, Sales Order, Scrap Request, Delivery Note, Department, Request, Stock Entry, Stock Ledger Entry.

### Scheduler Events
1. **Every 5 min**: BOM cost updates, pending harvesting transfers, email inbox reading.
2. **Every 30 min**: UOB file sync.
3. **Hourly**: Plaid sync, FOMS stock receipt updates.
4. **Daily 6 AM**: Reminder to submit draft invoices (Sales & Purchase).
5. **Daily 5 AM**: MinIO backup upload.
6. **Daily 11 PM**: Auto exchange rate revaluation.
7. **Monthly**: Asset depreciation entries, trial balance discrepancy notification.

### Override Whitelisted Methods
```python
override_whitelisted_methods = {
    "frappe.utils.print_format.download_pdf": "erpnext.controllers.pdf_utils.download_pdf_with_pagenum"
}
```
Replaces standard PDF download with version that adds page numbers.

### Custom Export Report
```python
custom_export_report = {
    "Balance Sheet": "erpnext.accounts.report.balance_sheet_v2.balance_sheet_v2.add_formulas",
    "Profit and Loss Statement": "erpnext.accounts.report.balance_sheet_v2.balance_sheet_v2.add_formulas",
    "Consolidated Financial Statement": "erpnext.accounts.report.balance_sheet_v2.balance_sheet_v2.add_formulas",
}
```
Injects Excel formulas when exporting financial reports.

### Validate Workflow Hook
```python
validate_workflow = {
    "Material Request": "erpnext.stock.doctype.material_request.material_request.validate_purchase_request"
}
```
Custom validation before workflow state transitions on Material Request.

### Sync Log Method Map
```python
sync_log_method = {
    1: "erpnext.controllers.foms._update_foms_supplier",
    2: "erpnext.controllers.foms._update_foms_customer",
    3: "erpnext.controllers.foms._update_warehouse",
    ...
}
```
Maps numeric sync type IDs to handler functions for FOMS data synchronization.

### Custom Email Footer
Default mail footer includes company URL (`erp.greenphyto.com`) from site config.

### MinIO Backup
1. `minio_backup_settings.py` handles automated database/file backups to MinIO object storage.
2. Supports custom bucket and folder configuration.
3. Two backup schedules: 5 AM and 8:40 PM daily.

### Scrap Entry Automation
1. Scrap requests auto-submit stock entries with custom expense accounts.
2. `submit directly scrap entry and custom account` allows bypassing manual submission step.

## Dependencies
- `erpnext.controllers.erp` (validate_company_selected, change_naming_series, various utility functions)
- `erpnext.controllers.foms` (sync_log, detect_salad_items, all FOMS sync handlers)
- `erpnext.controllers.pdf_utils` (download_pdf_with_pagenum)
- `erpnext.ai_agent` module (email_invoice, ai_agent_settings, ai_agent_memory)
- `erpnext.foms.doctype.minio_backup_settings` (backup automation)
- `erpnext.gp_erp.doctype.consignment_request` (consignment billing)
- `erpnext.controllers.uob` (UOB bank file sync)

## Notes
- The `css_include_custom` hook (`erpnext.startup.boot.get_css_custom`) allows dynamic CSS injection per company/user.
- `get_email_default` hook provides custom default email accounts based on document context.
- AI Agent Memory integration on Purchase Invoice submit is the newest addition (2026-07-03), enabling the AI to learn from submitted invoices.
- The `jinja.methods` section exposes `get_qrcode` and `get_barcode` for use in print formats.
- `quick_entry_js` for Item provides a custom quick entry form dialog.
