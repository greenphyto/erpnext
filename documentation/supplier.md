# Supplier

## Summary
Supplier code auto-generation with company-specific series, default account assignment by code prefix, supplier item restriction (Party Specific Item), bank list management, supplier validation for UOB payments, AI-powered supplier matching, and customer/supplier code unification.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 2a0631125d | fix fieldname supplier | 2026-03-31 |
| 3ec59d7055 | update customer code and supplier code | 2026-03-03 |
| dc7afe1485 | add MY for supplier code | 2026-03-03 |
| 0deda2a23d | disable filter company on customer and supplier | 2026-02-05 |
| 9ffdeff13b | strict customer and supplier | 2026-01-22 |
| 0393477e61 | Revert "fix default supplier from PR to PO" | 2025-12-03 |
| 203b426f05 | fix default supplier from PR to PO | 2025-12-01 |
| 27c7e14073 | uob: validate bank and company supplier match | 2025-11-19 |
| 3426f9fb16 | uob: supplier summary detail | 2025-09-09 |
| 752f855365 | advance supplier selecting | 2025-09-04 |
| e71bcf79f2 | update supplier | 2025-09-03 |
| 811cac98c1 | add supplier website | 2025-09-03 |
| e22832c3ab | update supplier domain with chat GPT | 2025-09-03 |
| 505337bdc3 | enhance supplier result | 2025-08-29 |
| 3f8dc1b1d1 | upgrade supplier context | 2025-08-29 |
| 75db2e32dd | fix non supplier issue | 2025-08-01 |
| 091862db6a | allow for missing supplier | 2025-07-18 |
| 6db1b1027a | add supplier from AI result | 2025-07-18 |
| 478569eb0b | advancing from no PO but have supplier | 2025-06-18 |
| 928d8270d0 | add bank list to supplier | 2025-05-20 |
| ... and 42 more commits |

## Affected Files
**Supplier Core**
- erpnext/buying/doctype/supplier/supplier.py
- erpnext/buying/doctype/supplier/supplier.js
- erpnext/buying/doctype/supplier/supplier.json
- erpnext/buying/doctype/supplier/test_supplier.py

**Supplier Code & Account Defaults**
- erpnext/accounts/doctype/supplier_code_account/supplier_code_account.py
- erpnext/accounts/doctype/supplier_code_account/supplier_code_account.json
- erpnext/accounts/doctype/default_account_by_code/default_account_by_code.py
- erpnext/accounts/doctype/default_account_by_code/default_account_by_code.json
- erpnext/buying/doctype/buying_settings/buying_settings.py
- erpnext/buying/doctype/buying_settings/buying_settings.js
- erpnext/buying/doctype/buying_settings/buying_settings.json

**Bank Integration**
- erpnext/accounts/doctype/bank_number/bank_number.py
- erpnext/uob/doctype/payment_approval/payment_approval.py
- erpnext/uob/doctype/payment_approval/payment_approval.js
- erpnext/uob/doctype/payment_approval/payment_approval.json

**Customer (parallel implementation)**
- erpnext/selling/doctype/customer/customer.py
- erpnext/selling/doctype/customer/customer.js
- erpnext/selling/doctype/customer/customer.json
- erpnext/selling/doctype/customer/test_customer.py
- erpnext/selling/doctype/customer_credit_limit/customer_credit_limit.json

**AI Agent (supplier matching)**
- erpnext/ai_agent/doctype/ai_agent_settings/ai_invoice_converter.py
- erpnext/ai_agent/doctype/email_invoice/email_invoice.py

**Item & Material Request**
- erpnext/stock/doctype/item/item.json
- erpnext/stock/doctype/item_list/item_list.py
- erpnext/stock/doctype/item_list/item_list.json
- erpnext/stock/doctype/material_request/material_request.py
- erpnext/stock/doctype/material_request/material_request.js
- erpnext/stock/doctype/material_request/material_request.json

**Controllers & Other**
- erpnext/accounts/party.py
- erpnext/controllers/accounts_controller.py
- erpnext/controllers/erp.py
- erpnext/controllers/foms.py
- erpnext/controllers/queries.py
- erpnext/controllers/va2.py
- erpnext/hooks.py
- erpnext/patches.txt
- erpnext/patches/v14_0/update_customer_name.py

## Flow/Logic

### Supplier Auto-Naming & Code Generation
1. `Supplier.autoname()` determines naming based on global setting `supp_master_name`:
   - "Supplier Name" → uses `supplier_name` as document name
   - "Naming Series" → uses `set_name_by_naming_series()`
   - Otherwise → uses meta autoname option
2. After naming, `set_code()` is called to generate `supplier_code`.

### Supplier Code Generation (`set_code`)
1. Gets company abbreviation from `Company.series_abbr`.
2. Uses `supplier_code_series` (default: `S0.####`) as the number pattern.
3. Prepends company abbreviation if not already in series (e.g., `SGS0.####` for SG company).
4. If `supplier_code` is empty, generates one via `parse_naming_series()`.
5. If code exists but missing company prefix, prepends it.
6. Validates uniqueness — throws error if supplier_code already used by another supplier.
7. Calls `set_account_default()` after code generation.

### Default Account Assignment by Code
1. `set_account_default()` reads `Buying Settings.default_supplier_account` child table.
2. Each row in the table maps a code prefix to a default account.
3. Matches supplier_code against code prefixes (with `...` removed).
4. If match found and no account row exists for the default company, appends one with the mapped account.

### Series Update Tracking
1. `update_series()` checks if the next value in the naming series matches the current supplier code.
2. If it matches, increments the series counter to prevent duplicate codes.
3. `get_exists_series()` is a whitelisted utility that previews the next series value without consuming it.

### Supplier Validation
1. `validate()` calls `set_code()` and `update_series()` to ensure code consistency.
2. Validates `naming_series` is set when global setting requires it.
3. `validate_party_accounts()` checks account currency matches.
4. `validate_internal_supplier()` prevents duplicate internal suppliers for the same company.

### Item-Supplier Restriction (Party Specific Item)
1. When `enable_item_supplier` is checked, the supplier's `item_supplier` table defines allowed items.
2. `validate_item_supplier()` creates/deletes `Party Specific Item` records to restrict which items can be purchased from this supplier.
3. On update: compares old vs. new item list, adds new restrictions, removes deleted ones.
4. When `enable_item_supplier` is unchecked, all restrictions are removed.

### Bank List for Supplier
1. `onload()` calls `load_bank_list()` from `bank_number` module.
2. Loads bank account details (account number, name, BIC) into the supplier form's onload data.
3. Used by Payment Approval to select the correct payee bank account.

### UOB Supplier Validation
1. Payment Approval validates that the supplier's bank matches the company bank.
2. Checks supplier bank number exists and has required details (account_no, account_name, currency).
3. For PayNow: validates proxy_number exists on the bank number record.

### AI-Powered Supplier Matching
1. AI invoice converter attempts to match supplier from extracted invoice data.
2. `add supplier from AI result` (`6db1b1027a`) — creates supplier record from AI extraction.
3. `advance supplier selecting` (`752f855365`) — improves matching algorithm.
4. `update supplier domain with chat GPT` (`e22832c3ab`) — enriches supplier data with domain info.
5. Handles missing supplier gracefully (`allow for missing supplier`, `fix non supplier issue`).

### Customer/Supplier Code Unification
1. Both Customer and Supplier follow the same code generation pattern with company prefix.
2. `update_customer_name.py` patch updates existing records to new naming format.
3. Company filter disabled on both customer and supplier lists (`0deda2a23d`) for cross-company visibility.

## Dependencies
- Buying Settings (stores default_supplier_account mapping table)
- Company (provides `series_abbr` for code prefix)
- Bank Number doctype (supplier bank account details)
- Party Specific Item (item restriction mechanism)
- UOB Payment Approval (consumes supplier bank data)
- AI Agent (supplier matching from invoices)
- NamingSeries (frappe utility for sequential numbering)

## Notes
- Supplier code format: `{company_abbr}{series}` e.g., `SGS0.0001`, `MYS0.0001` (MY prefix added in `dc7afe1485`).
- The `supplier_code_series` field is editable on the supplier form (`8bbaaa793e`) for manual override cases.
- `get_exists_series()` uses a fake counter that peeks at `current_value + 1` without incrementing — useful for preview.
- The `has_permission` function at module level grants access to all internal suppliers regardless of user restrictions.
- `strict customer and supplier` (`9ffdeff13b`) likely enforces stricter validation rules on party selection.
- Default supplier from PR to PO was reverted (`0393477e61`) after issues — the flow was pulling supplier from Purchase Receipt to Purchase Order incorrectly.
- Supplier `on_trash` cleans up primary contact, primary address, and all Party Specific Items.
