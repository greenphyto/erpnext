# Switch Company / Multi-Company

## Summary
Session-based company switching that allows users to operate within a specific company context. Includes a visual company indicator in the UI, company-specific theming/colors, User Permission auto-management, default value switching (currency, price lists, letter head, warehouse), strict permission enforcement, internal company transactions, and cross-tab synchronization.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 0613727c63 | add switch company between email entity | 2026-07-09 |
| 98ceafbda8 | switch company admin for asset depreciation | 2026-03-17 |
| d2d8dd9422 | mc: set inter company reference | 2025-12-12 |
| 80c41de1bc | mc: ignore permissions from internal company | 2025-12-02 |
| 6ef49798e9 | mc: add monthly net value for financial report | 2025-11-21 |
| a678846f4e | mc: auto set currency based on supplier | 2025-11-18 |
| 9bb7e6a7e2 | mc: auto create draft from purchase invoice | 2025-11-17 |
| 82bcd50b88 | mc: strict permissions for get list customer and supplier | 2025-11-13 |
| b65e9c81b8 | mc: add customer permissions | 2025-11-13 |
| 8c4ee1ce3d | mc: add switching theme between company | 2025-11-04 |
| f1d8ff0e75 | mc: get item from parent | 2025-10-24 |
| f09931faf2 | mc: add filter and adjust backend | 2025-10-24 |
| 9b94964576 | mc: default on backend | 2025-10-23 |
| 449c9bb400 | mc: Get letter head default | 2025-10-23 |
| d78884ee6b | mc: add abbriviation based on company | 2025-10-14 |
| fc411af960 | mc: adjust default based on company | 2025-10-07 |
| 6810def8bf | mc: add strict company option for some users | 2025-10-07 |
| 2c4e76266d | mc: validate multi company submit | 2025-10-02 |
| a6ecdfe289 | mc: switch company rule | 2025-10-02 |
| 61c26b5ed6 | mc: make settings enable/not | 2025-10-01 |
| e5020f761b | mc: switch company menu and html | 2025-10-01 |
| 5868ac8245 | mc: color settings | 2025-10-01 |
| 2986888e99 | mc: setup html view for indicator | 2025-09-30 |

... and 20 more commits

## Affected Files

**Core Switch Logic**
- erpnext/controllers/erp.py (switch_company, get_company_availabe, switch_default_values, validate_company_selected)
- erpnext/startup/boot.py (boot_session, get_company_selected, overide_user_defaults)
- erpnext/public/js/company_view.js (UI indicator and switcher dialog)

**Company Configuration**
- erpnext/setup/doctype/company/company.js
- erpnext/setup/doctype/company/company.json
- erpnext/accounts/doctype/accounts_settings/accounts_settings.json

**Permissions**
- erpnext/foms/doctype/company_permissions_list/company_permissions_list.py
- erpnext/foms/doctype/company_permissions_list/company_permissions_list.json
- erpnext/foms/doctype/customer_permissions_list/customer_permissions_list.py
- erpnext/foms/doctype/customer_permissions_list/customer_permissions_list.json

**Multi-Company Transactions**
- erpnext/controllers/accounts_controller.py
- erpnext/controllers/buying_controller.py
- erpnext/controllers/selling_controller.py
- erpnext/controllers/queries.py
- erpnext/accounts/doctype/sales_invoice/sales_invoice.py
- erpnext/buying/doctype/purchase_order/purchase_order.py
- erpnext/buying/doctype/supplier/supplier.py
- erpnext/selling/doctype/customer/customer.py
- erpnext/stock/doctype/delivery_note/delivery_note.py

**Financial Reports**
- erpnext/accounts/report/financial_statements.py
- erpnext/accounts/report/balance_sheet/balance_sheet.py
- erpnext/accounts/report/profit_and_loss_statement/profit_and_loss_statement.py

**Currency & Pricing**
- erpnext/accounts/doctype/currency_exchange_settings/currency_exchange_settings.py
- erpnext/accounts/doctype/currency_exchange_settings/currency_exchange_settings.js
- erpnext/setup/utils.py

**Part Number & Items**
- erpnext/foms/doctype/part_number_settings/part_number_settings.py
- erpnext/stock/__init__.py

**Hooks & Session**
- erpnext/hooks.py
- erpnext/foms/custom/letter_head.json

## Flow/Logic

### 1. Feature Toggle
Controlled by `Accounts Settings.enable_switch_company_menu`:
- `multi_entity_enable()` in `boot.py` checks if the field exists and is enabled
- If disabled, `company_selected` is set to `"Disabled"` and switching UI is hidden

### 2. Boot Session Initialization (`startup/boot.py:boot_session`)
On every page load:
1. Call `get_company_selected()` to determine current company
2. If not "ALL", load company color and set `bootinfo.sysdefaults.company` to selected company
3. Load company-specific letter heads
4. Check if user has `cannot_change_company` flag set
5. `overide_user_defaults()`: Override session defaults with company-specific values:
   - Currency, country, time_zone
   - Buying/selling price lists (matched by currency)
   - Letter head and content
   - Default warehouse
   - Cost center (explicitly set to empty)

### 3. Company Selection Resolution (`boot.py:get_company_selected`)
Priority order:
1. Session-based default value (from `user_session_log`)
2. User's `company_selected` field
3. Falls back to `"ALL"` if none set

### 4. Switch Company API (`controllers/erp.py:switch_company`)
When user clicks a company tile:
1. Check if user has `cannot_change_company` flag - block if set (unless `force=True`)
2. Update `User.company_selected` and `User.company` fields
3. Store in session defaults via `set_default_value()`
4. Update or create User Permission for Company (with `auto=1`, `hide_descendants=1`)
5. Skip User Permission for CEO role if `skip_ceo_role_from_strict_permissions` is enabled
6. Call `switch_default_values()` to update all dependent defaults

### 5. Default Values Switching (`controllers/erp.py:switch_default_values`)
Updates user-level defaults for:
- Company, currency, country, time_zone
- Letter head (company-specific)
- Buying price list (matched by currency)
- Selling price list (matched by currency)
- Default warehouse

### 6. UI Company Indicator (`public/js/company_view.js`)
- Displays a fixed-position badge showing current company name with color
- Color is stored on Company doctype and mapped to a Bootstrap light variant
- `frappe.show_switcher_company()`: Opens a tile-based dialog with all available companies
- On selection: calls `switch_company` API, then hard-reloads the page
- If on a Form view, navigates to List view first to avoid stale data

### 7. Cross-Tab Synchronization
`custom.listen_tab_change()`:
- Listens to window `focus` event
- Calls `get_company_selected` API to check if another tab switched companies
- If mismatch detected, triggers hard reload to sync

### 8. Company Validation on Submit (`controllers/erp.py:validate_company_selected`)
- Runs on document validate (via hooks)
- If document has a `company` field and user has a selected company
- Throws error if document's company doesn't match user's selected company
- Skipped for Administrator and when feature is disabled

### 9. Web-Based Switch (`switch_company_web`)
- Whitelisted endpoint for switching company via verified URL (e.g., from email links)
- Verifies request authenticity before switching

### 10. Internal Company Transactions
- Ignore permissions when creating documents for internal companies
- Auto-create draft Purchase Invoices from internal Sales Invoices
- Copy bill numbers across internal transactions
- Set inter-company references automatically

## Dependencies
- Accounts Settings (feature toggle: `enable_switch_company_menu`)
- User doctype (fields: `company_selected`, `cannot_change_company`, `company`)
- User Permission (auto-managed for Company restriction)
- Company doctype (fields: `color`, `theme_path`)
- User Session Log (session-based company storage)
- Letter Head (company-filtered)
- Price List (currency-matched)

## Notes
- The CEO role can be exempted from strict company permissions via `skip_ceo_role_from_strict_permissions` setting.
- Users with `cannot_change_company=1` are locked to their assigned company - the switch dialog shows "Company switching disabled".
- Company color uses a nearest-match algorithm to map arbitrary hex colors to Bootstrap light variants for the indicator background.
- The hard reload after switching clears Frappe's client-side cache to prevent showing data from the previous company.
- Cross-tab sync polls on window focus, not in real-time - there's a brief window where tabs can be out of sync.
- When `company_selected` is "ALL", no company filtering is applied (admin/CEO mode).
- The feature hooks into `validate` events on doctypes to enforce company matching - documents cannot be submitted against a different company than the user's current selection.
