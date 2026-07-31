# Tax

## Summary
Tax calculation features including GST Return Summary Report, TDS/withholding tax with item-wise calculation, Purchase Taxes and Sales Taxes reports, GST for Journal Entry (input tax claims via JV), and tax validation on item rows.

## Commits
| Hash | Message | Date |
|------|---------|------|
| ea5695949b | feat: enhance memory with tax details and apply tax template in PI creation | 2026-07-03 |
| 83c0cb9b90 | update sql syntax | 2026-03-10 |
| 2d52c04cb2 | hide taxes section | 2026-01-10 |
| 626e00dbf8 | prod: validate tax on item row | 2025-11-28 |
| 42d4051b62 | prod: tax on item row | 2025-11-28 |
| 00a395d7a6 | add tax amount | 2025-07-21 |
| 57441b0152 | fetch taxes | 2025-07-18 |
| 42310dc4c6 | add tax id from company | 2025-05-27 |
| 3e2f77c1ea | reactivate the function | 2025-02-26 |
| b5f5412889 | validate GST tax template | 2025-01-19 |
| fff953e871 | calculate taxable amount | 2024-11-19 |
| 5a911a2ab3 | add tax rate trigger | 2024-11-19 |
| 356010f8a2 | make ledger for GST entry | 2024-11-19 |
| 3404df2b17 | calculate taxable amount | 2024-11-18 |
| 3635c09205 | add taxable amount | 2024-11-18 |
| 222d83b168 | ad GST entry section | 2024-11-18 |
| 8795ffed27 | temporary hide GST Input Tax | 2024-11-18 |
| 17fbc89476 | GST return deposit | 2024-11-12 |
| 980d614df5 | categorize the tax | 2024-08-01 |
| f874a0c563 | add gst type | 2024-02-02 |
| 2732a4b0c1 | gst value for purchase | 2024-02-02 |
| 680243d52b | add gst input tax JV | 2024-02-02 |
| c8ff9eb8af | [feat] update view of tax without net amount | 2023-09-06 |
| fc2b566c09 | GST Columns added | 2023-01-30 |
| f3fe531550 | GST Detail | 2022-12-29 |
| ce5a769e09 | GST Detail | 2022-12-29 |
| b9fb1045d7 | feat: Item Wise TDS Calculation | 2022-11-06 |
| dcc6f5599d | gst return | 2022-11-04 |
| 70ff59cfc1 | gst return | 2022-11-04 |

## Affected Files

### GST for Journal Entry
- erpnext/accounts/doctype/gst_for_journal_entry/__init__.py
- erpnext/accounts/doctype/gst_for_journal_entry/gst_for_journal_entry.json
- erpnext/accounts/doctype/gst_for_journal_entry/gst_for_journal_entry.py

### Journal Entry (GST Integration)
- erpnext/accounts/doctype/journal_entry/journal_entry.js
- erpnext/accounts/doctype/journal_entry/journal_entry.json
- erpnext/accounts/doctype/journal_entry/journal_entry.py
- erpnext/accounts/doctype/journal_entry_account/journal_entry_account.json

### GST Return Summary Report
- erpnext/accounts/report/gst_return_summary_report/__init__.py
- erpnext/accounts/report/gst_return_summary_report/gst_return_summary_report.js
- erpnext/accounts/report/gst_return_summary_report/gst_return_summary_report.json
- erpnext/accounts/report/gst_return_summary_report/gst_return_summary_report.py
- erpnext/accounts/report/gst_return_summar_report/ (alternate spelling)

### Purchase Taxes Report
- erpnext/accounts/report/purchase_taxes/__init__.py
- erpnext/accounts/report/purchase_taxes/purchase_taxes.js
- erpnext/accounts/report/purchase_taxes/purchase_taxes.json
- erpnext/accounts/report/purchase_taxes/purchase_taxes.py

### Sales Taxes Report
- erpnext/accounts/report/sales_taxes/__init__.py
- erpnext/accounts/report/sales_taxes/sales_taxes.js
- erpnext/accounts/report/sales_taxes/sales_taxes.json
- erpnext/accounts/report/sales_taxes/sales_taxes.py

### Tax Withholding (TDS)
- erpnext/accounts/doctype/tax_withholding_category/tax_withholding_category.py
- erpnext/accounts/doctype/tax_withholding_category/test_tax_withholding_category.py

### Purchase Invoice Tax Fields
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.js
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.json
- erpnext/accounts/doctype/purchase_invoice_item/purchase_invoice_item.json
- erpnext/accounts/doctype/purchase_taxes_and_charges/purchase_taxes_and_charges.json

### Controllers
- erpnext/controllers/accounts_controller.py
- erpnext/controllers/taxes_and_totals.py
- erpnext/public/js/controllers/accounts.js
- erpnext/public/js/controllers/taxes_and_totals.js
- erpnext/public/js/controllers/transaction.js

### Patches
- erpnext/patches/v14_0/update_tds_fields.py

## Flow/Logic

### 1. GST Return Summary Report
- Report class `VATAuditReport` generates a GST return summary for a given period and company.
- Processes both Sales Invoice and Purchase Invoice doctypes.
- **Tax from GL Entry** (`get_tax_from_gl_entry()`):
  - Finds all tax account heads from Purchase/Sales Taxes and Charges Templates for the company.
  - Queries GL Entry for those accounts within the date range.
  - For Sales Invoices: uses `credit - debit` as output tax.
  - For Journal Entries: checks `je_voucher_type == "GST Input Tax"` or `tax_type == "Selling"` to determine direction.
  - For Purchase Invoices: uses `debit - credit` as input tax.
- **Summary Calculation**:
  - Output Tax Due (from sales)
  - Less: Input Tax and Refunds Claimed (from purchases)
  - Equals: Net GST to be paid/claimed
- Includes deleted/cancelled invoice data via `get_deleted_data()`.
- Groups items by tax rate using tax templates.

### 2. GST for Journal Entry
- Child doctype `GST for Journal Entry` added to Journal Entry.
- Fields: account, account_name, account_code, account_type, tax_rate, cost_center, account_currency, exchange_rate, debit_in_account_currency, debit, credit_in_account_currency, credit, user_remark, against_account, against_party.
- Allows claiming GST Input Tax via Journal Voucher entries.
- Journal Entry has `voucher_type` option "GST Input Tax" and `tax_type` field for categorization.
- Creates GL entries for the GST accounts when a GST JV is submitted.

### 3. Purchase Taxes Report
- Comprehensive purchase invoice register with tax breakdown.
- Columns: invoice details, supplier info, supplier group, tax_id, credit_to account, mode of payment, project, bill details, PO/PR references, currency.
- Expense accounts shown as individual columns with amounts.
- Handles `gst_input_tax` flag: if set, shows `base_value` instead of `net_total`.
- Shows `base_currency_of_base_value` for base currency amounts when GST input tax is applicable.
- Tax accounts shown separately from expense accounts.
- Totals: total tax, grand total, rounded total, outstanding amount.

### 4. Sales Taxes Report
- Similar structure to Purchase Taxes Report but for Sales Invoices.
- Shows customer details, debit_to account, income accounts, and tax breakdowns.

### 5. Item-Wise TDS (Tax Deducted at Source)
- Enhanced `tax_withholding_category.py` to calculate TDS at item level.
- Allows different TDS rates per item in a transaction.
- Patch `update_tds_fields.py` migrates existing TDS data to new field structure.

### 6. Tax Validation on Item Rows
- Purchase Invoice items can have per-row tax validation.
- Validates that tax template is correctly applied.
- `validate GST tax template`: Ensures correct GST template is selected based on transaction type.

### 7. Tax Rate Trigger (JS)
- Client-side tax rate calculation triggered on item/tax changes.
- `public/js/controllers/taxes_and_totals.js`: Recalculates taxable amounts when rates change.
- `public/js/controllers/accounts.js`: Handles tax account selection and rate display.

### 8. Taxable Amount Calculation
- Custom calculation of taxable amount per item for GST purposes.
- Supports scenarios where net amount differs from taxable amount (e.g., exemptions).
- `calculate taxable amount` logic in both Python controller and JS frontend.

### 9. AI Agent Tax Memory
- AI agent stores tax details in memory for applying correct tax templates when creating Purchase Invoices from email.
- Enhanced in commit ea5695949b to remember and apply tax templates automatically.

## Dependencies
- GL Entry doctype (tax amount queries)
- Purchase/Sales Taxes and Charges Template (tax account configuration)
- Journal Entry doctype (GST Input Tax voucher type)
- Tax Withholding Category doctype (TDS calculation)
- Accounts Settings (tax-related configurations)
- Purchase Invoice / Sales Invoice (tax row integration)
- AI Agent Memory (tax template auto-application)

## Notes
- The GST Return Summary Report uses GL Entry aggregation rather than invoice-level tax rows, providing a more accurate picture that includes journal entry adjustments.
- `gst_return_summar_report` (typo) directory exists alongside the correctly spelled `gst_return_summary_report` - likely a legacy version.
- The `GSTforJournalEntry` doctype is a simple pass-through class - all logic is handled in the parent Journal Entry's submit/cancel hooks.
- Journal Entry `voucher_type = "GST Input Tax"` is specifically for claiming GST credits via manual journal entries.
- The `tax_type` field on Journal Entry categorizes entries as "Selling" or "Buying" for correct GST report classification.
- Item-wise TDS calculation was introduced in v14 (2022-11-06) allowing granular withholding tax per line item rather than document-level only.
- The `hide taxes section` commit suggests certain tax UI sections are conditionally hidden based on context to simplify the user interface.
