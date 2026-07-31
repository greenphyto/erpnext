# Journal Entry

## Summary
Custom enhancements to the Journal Entry doctype including infinite loop prevention during rate changes, GST child table support (GST for Journal Entry), multi-currency adjustments, no-copy field enforcement, custom print format, and reference payment validation.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 6650a89d11 | fix infinite loop on journal entry | 2026-06-08 |
| 671211ccc7 | fix infinite loop rate change | 2026-05-31 |
| cf82e5dc99 | minimize journal entry row add | 2026-05-12 |
| 96c806fc17 | add journal entry for charges | 2026-03-30 |
| f59d41ba21 | add charge back journal entry | 2026-01-27 |
| 1f75780873 | adjust journal entry muti currency | 2025-12-24 |
| 00c7017e25 | link adjust journal entry in WIP report | 2025-12-18 |
| 2e77f1a887 | no copy for journal entry | 2025-04-15 |
| b54840b296 | no copy journal entry account | 2025-01-20 |
| 6614363868 | journal entry refund deposit | 2024-11-13 |
| e93575d20a | set no copy on journal entry | 2024-09-19 |
| 2a422cda25 | add journal entry to report GST | 2024-08-01 |
| 11a43d377c | fix journal entry multi currency | 2024-06-03 |
| a03e83382f | fix journal entry report | 2024-05-21 |
| b4a17d2855 | fix copying journal entry value | 2024-05-17 |
| dcf3f7b02e | add journal entry format | 2024-05-16 |
| 08cf24f153 | add account name to journal entry | 2024-04-29 |
| e73c7d5d37 | add journal entry report creditors | 2023-11-16 |
| c6026a3c0f | add journal entry | 2023-09-22 |
| a8cd90735c | add journal entry series | 2023-09-18 |
| 6aada76297 | fix: Opening journal entry templates | 2022-11-16 |
| faf25c0b95 | fix: Reference due date field type in Journal Entry Accounts table | 2022-10-26 |

## Affected Files
**Core Doctype:**
- erpnext/accounts/doctype/journal_entry/journal_entry.js
- erpnext/accounts/doctype/journal_entry/journal_entry.json
- erpnext/accounts/doctype/journal_entry/journal_entry.py
- erpnext/accounts/doctype/journal_entry_account/journal_entry_account.json
- erpnext/accounts/doctype/journal_entry_template/journal_entry_template.js

**GST Child Table:**
- erpnext/accounts/doctype/gst_for_journal_entry/__init__.py
- erpnext/accounts/doctype/gst_for_journal_entry/gst_for_journal_entry.json
- erpnext/accounts/doctype/gst_for_journal_entry/gst_for_journal_entry.py

**Print Format:**
- erpnext/accounts/print_format/journal_entry_general/__init__.py
- erpnext/accounts/print_format/journal_entry_general/journal_entry_general.html
- erpnext/accounts/print_format/journal_entry_general/journal_entry_general.json

**Reports:**
- erpnext/accounts/report/gst_return_summary_report/gst_return_summary_report.py
- erpnext/accounts/report/journal_entry_list/journal_entry_list.py
- erpnext/accounts/report/trade_debtors/trade_debtors.py
- erpnext/foms/report/wip_account_detail/wip_account_detail.py

**Controllers & Other:**
- erpnext/controllers/accounts_controller.py
- erpnext/hooks.py
- erpnext/public/js/controllers/transaction.js

## Flow/Logic

### Infinite Loop Prevention
1. In `journal_entry.js`, when `exchange_rate` or `currency_base` changes, the code iterates over `accounts` rows and updates `debit`/`credit` based on account currency.
2. The loop was triggered because setting debit/credit on a row re-triggered the field change event. Fix ensures the update only fires when the row's `account_currency` matches `currency_base`, preventing recursive triggering.

### GST Child Table (GST for Journal Entry)
1. A new child doctype `GST for Journal Entry` is defined as a table (`istable: 1`) with fields: account, account_name, account_code, tax_rate, debit/credit in account currency, debit/credit in company currency, exchange_rate, cost_center, user_remark.
2. When `voucher_type` is "Journal Entry with GST", the parent JE shows a `gst_entry` child table.
3. `validate_gst_input()` in `journal_entry.py` enforces:
   - For "GST Input Tax" type: `party_name` and `invoice_no` must be set.
   - For "Journal Entry with GST" type: `tax_template_` must be set if `gst_entry` rows exist.

### Multi-Currency Handling
1. `currency_base` field on the parent allows selecting a foreign currency.
2. On change, `set_exchange_rate_on_parent` fetches the rate.
3. `exchange_rate` change iterates all account rows where `account_currency == currency_base` and recalculates debit/credit in company currency using the exchange rate.

### No-Copy Enforcement
1. Fields like `debit_in_account_currency`, `credit_in_account_currency`, `debit`, `credit`, `exchange_rate`, `user_remark` on Journal Entry Account are marked `no_copy: 1`.
2. This prevents values from being carried over when duplicating a Journal Entry, avoiding stale data.

### Reference Payment Validation
1. `validate_reference_payment()` checks `Accounts Settings.mandatory_reference_on_journal_entry`.
2. If enabled, for Payable accounts with debit > 0 (not advance), a reference document is required.
3. Similarly for Receivable accounts with credit > 0 (not advance).

### Cost Center Validation
1. `validate_cost_center()` iterates accounts rows.
2. Only enforces cost center on Profit & Loss accounts (skips Balance Sheet accounts).
3. Attempts to get a default cost center from `erpnext.get_default_cost_center()`.
4. Throws error if no cost center found for P&L accounts.

## Dependencies
- `erpnext.controllers.accounts_controller.AccountsController` (parent class)
- `erpnext.accounts.utils` (get_account_currency, get_balance_on)
- Accounts Settings (`mandatory_reference_on_journal_entry` flag)
- Sales/Purchase Taxes and Charges Templates (for GST voucher type)
- FOMS Integration (rate_card, WIP report linking)

## Notes
- The "Easy Depreciation" button in JS is marked as "Under construction" and throws an error if clicked.
- The `voucher_type` field supports custom types: "GST Input Tax", "Journal Entry with GST" beyond standard ERPNext types.
- `transaction_type` field (Selling/Buying) controls which tax template and invoice type filters are used for GST entries.
- The `invoice_no` field change fetches `grand_total` and party from the linked invoice to pre-fill `base_value` and `party_name`.
