# Cost Center

## Summary
Comprehensive cost center management: auto-loading cost center from account mappings, mandatory cost center validation for P&L accounts, Cost Center Settings doctype for company-wide account-to-cost-center mapping, locking behavior for Balance Sheet accounts (codes starting with 1/2/3), and default cost center logic throughout transactions.

## Commits
| Hash | Message | Date |
|------|---------|------|
| bd97ac903f | set default cost center if missing | 2026-07-23 |
| d97ffa3578 | make bold on cost center name and end line | 2026-06-23 |
| 5f6ee251b6 | fix filter cost center ambigue | 2026-06-23 |
| 051825323a | updating cost center pathces | 2026-06-22 |
| 72f5556eee | fix depreciation cost center | 2026-06-22 |
| f9d05a7ecf | fix cost center view | 2026-06-18 |
| 2ca98da7ec | validate cost center for PL account | 2026-06-05 |
| faaf83cbd4 | fix cost center setting for sales invoice | 2026-06-05 |
| e315545671 | fix cost center on ledger report | 2026-06-05 |
| 23977c71ba | add pacthes for acount cost center | 2026-06-05 |
| 5b25267aff | get cost center from account | 2026-06-04 |
| 92ebd1dd17 | make cost center default empty and mandatory | 2026-06-04 |
| 81ab1df7fd | hide total company and add total cost centers | 2026-05-16 |
| cfff032080 | filter cost center based on company | 2026-05-12 |
| 2ccaaa174e | add copy cost center | 2026-04-22 |
| 31edb26b3e | fix cost center and GST on AI invoice | 2026-02-19 |
| a2605efc55 | fix default cost center and warehouse | 2026-02-13 |
| 31303b8046 | prod: basic looping repot each cost center | 2025-11-27 |
| 5a6f16a2aa | prod: show cost center on columns | 2025-11-25 |
| 1254d35aed | prod: copy cost center settings | 2025-10-27 |

... and 32 more commits

## Affected Files

**Core Cost Center**
- erpnext/accounts/doctype/cost_center/cost_center.py
- erpnext/accounts/doctype/cost_center/cost_center.js
- erpnext/accounts/doctype/cost_center/cost_center.json

**Cost Center Settings (Custom)**
- erpnext/foms/doctype/cost_center_settings/cost_center_settings.py
- erpnext/foms/doctype/cost_center_settings/cost_center_settings.js
- erpnext/foms/doctype/cost_center_settings/cost_center_settings.json

**Cost Center Mapping**
- erpnext/accounts/doctype/cost_center_mapping/cost_center_mapping.py
- erpnext/accounts/doctype/cost_center_mapping/cost_center_mapping.json

**GL Entry Validation**
- erpnext/accounts/doctype/gl_entry/gl_entry.py
- erpnext/accounts/doctype/gl_entry/gl_entry.json
- erpnext/accounts/general_ledger.py

**Transaction Controllers**
- erpnext/controllers/accounts_controller.py
- erpnext/controllers/erp.py
- erpnext/controllers/erp_api.py
- erpnext/controllers/foms.py

**Utils & Defaults**
- erpnext/__init__.py
- erpnext/accounts/utils.py
- erpnext/startup/boot.py

**Invoices & Documents**
- erpnext/accounts/doctype/sales_invoice/sales_invoice.py
- erpnext/accounts/doctype/sales_invoice/sales_invoice.js
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.js
- erpnext/accounts/doctype/journal_entry/journal_entry.py
- erpnext/accounts/doctype/journal_entry/journal_entry.js
- erpnext/accounts/doctype/payment_entry/payment_entry.py
- erpnext/accounts/doctype/payment_entry/payment_entry.js

**Item Tables (JSON schema changes)**
- erpnext/accounts/doctype/sales_invoice_item/sales_invoice_item.json
- erpnext/accounts/doctype/purchase_invoice_item/purchase_invoice_item.json
- erpnext/stock/doctype/delivery_note_item/delivery_note_item.json
- erpnext/stock/doctype/purchase_receipt_item/purchase_receipt_item.json

**Reports**
- erpnext/accounts/report/financial_statements.py
- erpnext/accounts/report/profit_and_loss_statement/profit_and_loss_statement.py
- erpnext/accounts/report/general_ledger/general_ledger.py

**Assets**
- erpnext/assets/doctype/asset/asset.py
- erpnext/assets/doctype/asset/depreciation.py

**Patches**
- erpnext/patches/gp/set_default_cost_center_in_account.py
- erpnext/patches.txt

## Flow/Logic

### 1. Default Cost Center Resolution (`erpnext/__init__.py:get_default_cost_center`)
When a cost center is needed for a transaction:
1. Look up the `cost_center` field on the Account document itself
2. If not found, check `Cost Center Mapping` doctype for a (company, account) pair
3. Return the mapped cost center or empty string

### 2. Cost Center from Account with Lock Logic (`accounts/utils.py:get_cost_center_from_account`)
Returns `{"value": cost_center, "lock": 0|1}`:
1. Call `get_default_cost_center()` - if found, return with `lock=1` (user cannot override)
2. If account number starts with 1, 2, or 3 (Balance Sheet accounts), return empty with `lock=1` (no cost center allowed)
3. Otherwise return empty with `lock=0` (user can manually set)

### 3. Auto-Set Cost Center on Transactions (`accounts_controller.py:set_cost_center_by_settings`)
Runs during `validate()` on Sales Invoice, Delivery Note, Purchase Order, Purchase Invoice, Purchase Receipt:
1. For each item row, determine the relevant account (income_account or expense_account)
2. Call `get_cost_center_from_account(account, company)`
3. If `lock=1`: force the mapped cost center (or keep existing if no mapping)
4. If `lock=0` and a cost center was found: set it as default (user can still change)

### 4. GL Entry Validation (`gl_entry.py`)
On GL Entry validate:
1. `set_default_cost_center_value()`: Only for P&L accounts - auto-fills cost center from mapping if blank
2. `pl_must_have_cost_center()`: P&L accounts MUST have a cost center. Exception: Period Closing Voucher and entries with posting date before current fiscal year (`allow_cost_center_missing()`)
3. `validate_cost_center()`: Ensures cost center belongs to the correct company and is not a group node

### 5. Cost Center Settings Doctype (`foms/doctype/cost_center_settings`)
A company-level configuration page:
- Holds a child table mapping accounts to cost centers
- `load_from_accounts()`: Loads all non-group accounts, preserves existing mappings, adds new accounts
- `on_update()`: Syncs mappings back to Account doctype's `cost_center` field
- Sorted by account_number for easy navigation

### 6. Boot Session Defaults
During session boot (`startup/boot.py`):
- `cost_center` default is explicitly set to empty string (`""`) to prevent inheriting stale values
- Forces users to get cost center from account mapping rather than a global default

### 7. Fiscal Year Exception
`allow_cost_center_missing()` in `gl_entry.py`:
- If a GL entry's posting date is before the current fiscal year start date, cost center is not mandatory
- This allows historical corrections without requiring cost center backfill

## Dependencies
- Account doctype (stores `cost_center` field for direct mapping)
- Cost Center Mapping doctype (alternative mapping table)
- Cost Center Settings (FOMS custom doctype for bulk management)
- Accounts Settings (company-level configuration)
- GL Entry (enforcement point)

## Notes
- The lock mechanism prevents users from overriding cost centers for accounts that have explicit mappings or are Balance Sheet accounts (starting with 1/2/3).
- Account numbers starting with 1, 2, 3 are assumed to be Balance Sheet accounts - this is a convention-based check, not metadata-driven.
- Cost center is explicitly blanked on boot session to avoid cross-company contamination in multi-company setups.
- The `allow_cost_center_missing()` grace period only applies to entries before the current fiscal year - useful during migration or historical adjustments.
- Duplicate settings exist: both `Cost Center Mapping` doctype and Account's own `cost_center` field serve as mapping sources. The Settings doctype syncs to the Account field on save.
