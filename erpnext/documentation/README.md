# GP ERPNext v14 - Custom Features Documentation

## About

This folder documents all custom changes made in branch **gpprod.v14.3.1** compared to the base **v14.3.1-fresh-new** (vanilla ERPNext v14.3.1).

## Branch Context

| Branch | Description |
|--------|-------------|
| `v14.3.1-fresh-new` | Base snapshot of vanilla ERPNext v14.3.1 (orphan, 1 commit) |
| `gpprod.v14.3.1` | Production branch with all GP customizations |

## File Format Standard

Every `.md` file in this folder follows this structure:

```markdown
# Feature Name

## Summary
One-paragraph description of what this feature does and why it exists.

## Commits
| Hash | Message | Date |
|------|---------|------|
| abc123 | feat: description | 2026-01-01 |

## Affected Files
- path/to/file.py — purpose
- path/to/file.js — purpose

## Flow/Logic
Step-by-step explanation of how the feature works, from trigger to outcome.

## Dependencies
Other features or modules this depends on.

## Notes
Edge cases, known issues, things future developers should watch out for.
```

## Index

### Core Business Logic

| File | Feature | Description |
|------|---------|-------------|
| [batch_management.md](batch_management.md) | Batch Status & Lifecycle Tracking | Custom batch states, expiry, FOMS batch integration |
| [cost_center.md](cost_center.md) | Cost Center Auto-load & Validation | Auto-load from account, mandatory for PL accounts |
| [invoice_and_billing.md](invoice_and_billing.md) | Invoice Over-billing Validation & Tax | Over-billing prevention, tax handling on SI/PI |
| [payment.md](payment.md) | Payment Approval & UOB Integration | Payment entry workflow, UOB bank file generation |
| [delivery_note.md](delivery_note.md) | Delivery Note Workflow & Packing Slip | DN custom fields, packing slip integration |
| [manufacturing.md](manufacturing.md) | Work Order, BOM & Production Plan | Operation defaults, workstation, job card |
| [stock_and_inventory.md](stock_and_inventory.md) | Stock Ledger & Inventory Dimension | Item department, part number, FOMS data mapping |
| [naming_series.md](naming_series.md) | Naming Series & Custom Numbering | Company-specific numbering patterns |
| [search_and_filters.md](search_and_filters.md) | Item Search, Filters & Query Override | Custom get_query, link filters, search overrides |
| [packaging_and_weight.md](packaging_and_weight.md) | Packaging, Carton UOM & Weight Tracking | Package size, carton UOM, total KG |
| [supplier.md](supplier.md) | Supplier Part Number & Auto-fetch | Supplier item codes, auto-fetch details |
| [switch_company.md](switch_company.md) | Switch Company (Multi-Entity Context) | Session-based company switching, multi-entity admin |
| [consignment_flow.md](consignment_flow.md) | Consignment Order & Request Flow | Inter-entity consignment workflow |

### Financial & Accounting

| File | Feature | Description |
|------|---------|-------------|
| [financial_statements.md](financial_statements.md) | Financial Statements (Consolidation & Cash Flow) | Balance sheet v2, cash flow GP, consolidation |
| [journal_entry.md](journal_entry.md) | Journal Entry (GST Child Table & Loop Fix) | GST for JE, infinite loop prevention |
| [tax.md](tax.md) | Tax (GST Return, TDS, Withholding) | GST summary report, purchase/sales taxes |
| [budget.md](budget.md) | Budget Variance Report & Validation | Monthly variance tracking |
| [debtors_and_creditors.md](debtors_and_creditors.md) | Trade Debtors & Creditors Reports | Receivable/payable aging reports |
| [currency_and_exchange_rate.md](currency_and_exchange_rate.md) | Multi-Currency & Exchange Rate Fetch | Auto-fetch rates, currency settings |
| [asset_and_depreciation.md](asset_and_depreciation.md) | Asset Depreciation & Capitalization | Skip month, change log, custom disposal |
| [disposal_entry.md](disposal_entry.md) | Asset Disposal Entry | Custom date, draft save, posting validation |
| [pl_performance_report.md](pl_performance_report.md) | PL Performance Review Report | P&L performance analysis |

### Integration & Sync

| File | Feature | Description |
|------|---------|-------------|
| [foms_integration.md](foms_integration.md) | FOMS Integration & Data Mapping | Factory order management system sync |
| [data_sync.md](data_sync.md) | FOMS Data Sync (Minio, UOB File) | Minio backup, UOB file sync |
| [bank_and_reconciliation.md](bank_and_reconciliation.md) | UOB Bank Reconciliation & SWIFT | Bank charges, BIC codes, file sending |
| [ai_email_invoice.md](ai_email_invoice.md) | AI Email Invoice | Auto-create PI from email via Google Vision OCR |
| [swagger_api.md](swagger_api.md) | Swagger API Documentation | Interactive API docs for external systems |
| [api.md](api.md) | ERP API Endpoints | REST API for FOMS and external integrations |
| [import_export.md](import_export.md) | Import/Export & Minio Upload | CSV generation, Minio upload, download logging |

### Stock & Warehouse

| File | Feature | Description |
|------|---------|-------------|
| [stock_entry.md](stock_entry.md) | Stock Entry Custom Purpose & Scrap | Custom SE types, scrap request integration |
| [warehouse.md](warehouse.md) | Warehouse Barcode & Default Setup | Barcode system, default warehouse logic |
| [uom_management.md](uom_management.md) | UOM Default & Conversion Management | FOMS UOM mapping, conversion overrides |
| [price_list.md](price_list.md) | Price List Rate Validation & Notifications | Rate validation, missing price alerts |
| [stock_account_reposting.md](stock_account_reposting.md) | Stock/Account Reposting Error Handling | Error emails, repost settings fixes |
| [waste_management.md](waste_management.md) | Waste Tracking & Notification | Product waste notification, scrap from WO |

### Selling & Buying

| File | Feature | Description |
|------|---------|-------------|
| [sales_order.md](sales_order.md) | Sales Order Custom Fields & Workflow | Custom fields, workflow changes |
| [customer.md](customer.md) | Customer Packaging & Custom Fields | Customer packaging prefs, auto-fetch |
| [bulk_upload_forecast.md](bulk_upload_forecast.md) | Bulk Upload Forecast | CSV upload with preview, DataTable, auto-submit |
| [forecast_settings.md](forecast_settings.md) | Forecast Settings & Lead Time Sync | Lead time API, request creation |
| [request_calendar.md](request_calendar.md) | Request Calendar | Visual calendar for Request doctype |

### Reports & Print

| File | Feature | Description |
|------|---------|-------------|
| [reports.md](reports.md) | Custom Reports | Stock ageing, GL, balance sheet, sales analytics |
| [print_and_pdf.md](print_and_pdf.md) | Print Format & PDF Templates | Custom print for SI, DN, packing slip, CO |

### System & Infrastructure

| File | Feature | Description |
|------|---------|-------------|
| [settings_and_configuration.md](settings_and_configuration.md) | System Settings & Configuration | Company/buying/selling/stock settings |
| [hooks_and_customization.md](hooks_and_customization.md) | Hooks, Overrides & Custom Logic | doc_events, override methods |
| [permissions_and_roles.md](permissions_and_roles.md) | Permissions, Roles & Access Control | Role-based restrictions |
| [email_and_notifications.md](email_and_notifications.md) | Email Notifications & Templates | Business event notifications |
| [scheduler.md](scheduler.md) | Scheduler & Background Jobs | Reorder, sync, background tasks |
| [patches_and_migration.md](patches_and_migration.md) | Data Patches & Migration Scripts | One-time data fixes and migrations |

### Combined

| File | Description |
|------|-------------|
| [bugfixes_and_minor_changes.md](bugfixes_and_minor_changes.md) | Bug fixes, chores, cleanup, testing, and minor changes (~1,201 commits) |

## How to Update This Documentation

When adding a new feature or making significant changes:

1. Check if an existing `.md` file covers the area you changed
2. If yes: add a new row to the Commits table, update Flow/Logic if the behavior changed
3. If no: create a new `.md` file using the format standard above, then add it to this README index
4. For bug fixes and minor changes: append to `bugfixes_and_minor_changes.md` under the relevant module section

### Naming Convention

- Use lowercase with underscores: `feature_name.md`
- Name should be specific and descriptive (e.g., `ai_email_invoice.md`, not `ai.md`)
- Avoid generic names like `fixes.md` or `updates.md`

### When to Create a New File vs Update Existing

- **New file**: The change introduces a new workflow, new doctype, or new integration
- **Update existing**: The change enhances, fixes, or extends an already-documented feature
- **Bugfixes file**: One-off fixes that don't change the overall feature logic

## Reference

- Production branch: `gpprod.v14.3.1`
- Base branch: `v14.3.1-fresh-new`
- Repository: `https://github.com/greenphyto/erpnext.git`
