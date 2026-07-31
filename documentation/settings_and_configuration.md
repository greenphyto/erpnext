# Settings & Configuration

## Summary
System settings and configuration defaults across GP ERPNext including company settings, buying/selling settings, stock settings, manufacturing settings, per-session company defaults, AI settings, bank purpose configuration, and scrap/asset account settings.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 95ed2b946c | add enable settings | 2026-05-04 |
| 5aa4941a86 | per session company default settings | 2026-04-29 |
| bfefa05ce6 | check setting allow multiple companies | 2026-04-08 |
| f70457d96a | add company admin settings | 2026-03-10 |
| 28f440ee71 | add default 1 year range | 2026-03-03 |
| 8645f0b028 | create AI settings based on company | 2026-02-18 |
| b0557b6ad4 | status configuration from SE and SI | 2026-02-09 |
| de957d2c85 | add scrap delay settings | 2026-01-20 |
| 9ef3f68082 | create setting to disable change company | 2026-01-13 |
| b34e685414 | add setting field | 2025-12-23 |
| ae8f6e94d5 | add scrap account settings | 2025-12-08 |
| fbf000243e | ai; add threshold settings | 2025-11-06 |
| ba5513dcca | add default tax as 9 percent | 2025-07-31 |
| 99cda655a9 | update item name based on settings | 2025-07-07 |
| d713523519 | enable set default bank account and quick entry | 2025-07-04 |
| 389c32c9da | not use default expense account if purchase stock item | 2025-06-02 |
| 9a1e169a6e | setup type and method view | 2025-05-26 |
| 5e4ba59a2b | add bank purpose and add default | 2025-05-26 |
| 2fbba301cd | change settings | 2025-04-30 |
| f0dad9d11d | add settings | 2025-04-24 |

## Affected Files
**Company Settings**
- erpnext/setup/doctype/company/company.json
- erpnext/setup/doctype/company/company.py
- erpnext/setup/doctype/company/test_company.py
- erpnext/patches/v14_0/update_company_settings.py
- erpnext/patches/v14_0/add_company_admin_user.py

**Buying & Selling Settings**
- erpnext/buying/doctype/buying_settings/buying_settings.json
- erpnext/selling/doctype/selling_settings/selling_settings.json
- erpnext/selling/doctype/customer/customer.json

**Stock Settings**
- erpnext/stock/doctype/stock_settings/stock_settings.json
- erpnext/stock/doctype/item/item.js
- erpnext/stock/doctype/item/item.json
- erpnext/stock/doctype/item/item.py

**Manufacturing Settings**
- erpnext/manufacturing/doctype/manufacturing_settings/manufacturing_settings.json

**FOMS/UOB Integration Settings**
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.json
- erpnext/foms/doctype/minio_backup_settings/minio_backup_settings.py
- erpnext/uob/doctype/uob_integration_settings/uob_integration_settings.py
- erpnext/uob/doctype/uob_integration_settings/uob_integration_settings.json

**Bank Purpose**
- erpnext/foms/doctype/bank_purpose/bank_purpose.py
- erpnext/foms/doctype/bank_purpose/bank_purpose.json
- erpnext/patches/gp/add_bank_purpose.py

**Session & Boot**
- erpnext/startup/boot.py
- erpnext/public/js/company_view.js
- erpnext/gp_erp/doctype/user_session_log/user_session_log.py

**Hooks & Controllers**
- erpnext/hooks.py
- erpnext/controllers/erp.py
- erpnext/controllers/foms.py
- erpnext/public/js/controllers/transaction.js
- erpnext/stock/get_item_details.py

## Flow/Logic

### Per-Session Company Defaults
1. On login/session start, the system loads company-specific defaults into the session via `boot.py`.
2. `user_session_log` tracks which company each user is currently working in.
3. A setting (`disable_change_company`) prevents users from switching companies mid-session.
4. `allow_multiple_companies` controls whether multi-company selection is permitted.
5. `company_view.js` manages the UI for company switching.

### Company Admin Settings
1. Each company has a designated `company_admin` user (added via `add_company_admin_user` patch).
2. `switch_to_company_admin(company)` function allows background jobs to execute as the company's admin user.
3. Used by sync operations and scheduled tasks that need company-specific permissions.

### Default Account Configuration
1. Company doctype extended with custom fields: `cost_center_for_production`, `cost_center_for_packing`, `default_cost_expense_account`, `production_loss_account`.
2. Scrap account settings define where scrap/waste expenses are booked.
3. Default bank account settings enable quick entry workflows.
4. Default tax rate (9%) is set for new tax templates.

### Item Name & Settings
1. Item naming can be controlled by settings - update item name based on configured rules.
2. `not use default expense account if purchase stock item` - stock items use stock-in-hand account instead of expense.
3. `get_item_details.py` uses these settings to determine account selection at transaction time.

### Bank Purpose Configuration
1. `Bank Purpose` doctype categorizes bank transactions (payment types, purposes).
2. Patch `add_bank_purpose` creates default bank purpose records.
3. Used in payment entry workflows to classify transactions.

### AI Settings
1. AI agent settings are created per-company.
2. Threshold settings control when AI processing triggers (e.g., invoice conversion confidence threshold).
3. Company-specific AI configuration allows different processing rules per entity.

### Scrap & Manufacturing Settings
1. Scrap delay settings control timing for scrap request processing.
2. Manufacturing settings extended with: default FG warehouse, default scrap warehouse, enable attrition qty, default expense account.
3. Stock entry type views (Seeding Transfer, Transplanting Transfer, Harvesting Transfer, etc.) configured for manufacturing flow.

### Fiscal Year & Date Range
1. Default 1-year range setting for report date filters.
2. Fiscal year validation in `fiscal_year.py` ensures proper period boundaries.

## Dependencies
- Company doctype (central configuration hub)
- User Session Log (tracks active company per user)
- Boot.py (loads session defaults on login)
- Hooks.py (registers document events and scheduler jobs)
- FOMS Integration Settings (external system configuration)
- Manufacturing Settings (production workflow defaults)

## Notes
- Company settings cascade: company-level overrides system-level defaults.
- The `switch_to_company_admin()` pattern is critical for background jobs that need to respect company-specific permissions.
- `stock_settings.json` and `buying_settings.json` have custom fields added for GP-specific workflows (e.g., default warehouse per item group).
- The `enable` toggle pattern is used throughout - settings can be individually enabled/disabled without removal.
- Bank purpose and payment approval workflows are tightly coupled - changing bank purpose affects payment routing.
- Per-session company isolation prevents data leakage between companies in multi-company setups.
