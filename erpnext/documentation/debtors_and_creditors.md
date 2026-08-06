# Trade Debtors & Creditors Reports

## Summary
Custom reports for tracking trade receivables and payables. Includes detailed line-item reports (Trade Debtors, Trade Creditors) and summarized party-level reports (Trade Debtors Summary, Trade Creditors Summary). Reports filter accounts by `is_trade_related` flag and show ageing buckets, outstanding amounts, and support original currency display.

## Commits
| Hash | Message | Date |
|------|---------|------|
| dd6bae5c13 | fix filters trade debtors | 2026-06-18 |
| bec9a19500 | fixing trade creditors invoice | 2026-04-24 |
| 417d593078 | fix trade creditor report | 2026-01-20 |
| e2ec25df2a | add supplier code trade debtors | 2024-11-25 |
| b11140e90f | Update trade_debtors_summary.js | 2023-03-10 |
| 0084b10695 | Update trade_creditors_summary.js | 2023-03-10 |
| 4056151d7b | fix missing records on other debtors | - |
| 85a9fd1b19 | fix bug missing accounts | - |
| 97cd8054c7 | add safe abs to all doctype | - |
| 5a2b6a2759 | add account code | - |
| 53d1cc033e | add dute date to summary | - |
| e890305660 | change default filter ageing | - |
| 57d463dcd0 | add not due date | - |

## Affected Files
**Core report engine (shared)**
- erpnext/accounts/report/trade_debtors/trade_debtors.py (DebtorCreditorReport class)

**Trade Debtors (detail)**
- erpnext/accounts/report/trade_debtors/trade_debtors.js
- erpnext/accounts/report/trade_debtors/trade_debtors.json

**Trade Creditors (detail)**
- erpnext/accounts/report/trade_creditors/trade_creditors.py
- erpnext/accounts/report/trade_creditors/trade_creditors.js
- erpnext/accounts/report/trade_creditors/trade_creditors.json

**Trade Debtors Summary**
- erpnext/accounts/report/trade_debtors_summary/trade_debtors_summary.py (TradeDebtorsSummary class)
- erpnext/accounts/report/trade_debtors_summary/trade_debtors_summary.js
- erpnext/accounts/report/trade_debtors_summary/trade_debtors_summary.json

**Trade Creditors Summary**
- erpnext/accounts/report/trade_creditors_summary/trade_creditors_summary.py
- erpnext/accounts/report/trade_creditors_summary/trade_creditors_summary.js
- erpnext/accounts/report/trade_creditors_summary/trade_creditors_summary.json

**Patches**
- erpnext/patches/trade_creditors_issue/

## Flow/Logic

### DebtorCreditorReport (trade_debtors.py)
1. **Initialization**: Sets defaults including `dr_or_cr` (debit for Customer, credit for Supplier), determines the default receivable/payable account from Company settings.
2. **Account Filtering**: Instead of filtering by `account_type = Receivable/Payable`, it filters accounts where `is_trade_related = 1` under the appropriate `root_type` (Asset for Customer, Liability for Supplier). Then further filters to child accounts of that trade-related parent with the correct `account_type`.
3. **PLE Query**: Queries `Payment Ledger Entry` joined with Party table (for party_code) and Account table (for account_code, account_name). For Journal Entries, applies an additional filter to only show entries hitting the receivable/payable account.
4. **Voucher Balance Calculation**: Iterates PLE entries and builds an OrderedDict keyed by `(voucher_type, voucher_no, party)`. Tracks invoiced, paid, and credit_note amounts.
5. **Outstanding Calculation**: `outstanding = invoiced - paid - credit_note`. Only rows with non-zero outstanding are included.
6. **Payment Terms Allocation**: If `based_on_payment_terms` filter is set, splits invoice rows by payment schedule using FIFO allocation.
7. **Ageing**: Calculates age in days based on the selected ageing method (Due Date, Posting Date, or Supplier Invoice Date). Assigns outstanding to one of 5 ageing buckets (range1-range5). Amounts not yet due go to `not_due_yet`.
8. **Future Payments**: Optionally shows future-dated Payment Entries and Journal Entries not yet posted.
9. **Group by Party**: Optionally groups rows by party with subtotals.
10. **Original Currency**: When enabled, displays amounts in account currency instead of company currency.

### Trade Creditors (trade_creditors.py)
- Simply calls `DebtorCreditorReport` with `party_type = "Supplier"`.

### TradeDebtorsSummary (trade_debtors_summary.py)
1. Runs the full `DebtorCreditorReport` to get line-item receivables.
2. Aggregates by `(party, party_account)` into `party_total` dict summing all currency fields and ageing buckets.
3. Fetches advance payment amounts via `get_partywise_advanced_payment_amount` with "Trade" filter.
4. Subtracts advance from paid amount and shows advance in a separate column.
5. Optionally shows GL balance and difference (for reconciliation).

### Trade Creditors Summary
- Reuses `TradeDebtorsSummary` class with `party_type = "Supplier"`.

### Key Columns
- Party, Party Code, Account Code, Account Name, Voucher Type/No, Due Date, Invoiced, Paid, Credit/Debit Note, Outstanding, Age, Not Due Yet, Ageing Buckets (5 ranges), Currency.

## Dependencies
- Payment Ledger Entry (ple) - core data source
- Account doctype - `is_trade_related` custom field
- `erpnext.accounts.party.get_partywise_advanced_payment_amount` - advance calculation
- `frappe.utils.safe_abs` - used instead of built-in abs

## Notes
- The `is_trade_related` flag on Account is a GP custom field that distinguishes trade accounts from other receivable/payable accounts.
- Journal Entry filtering uses the party_account filter or falls back to the company default receivable/payable account to avoid showing JE lines that hit non-trade accounts.
- The `party_code` field (customer_code/supplier_code) is fetched via LEFT JOIN on the party table.
- Summary reports skip total row when `show_original_currency` is enabled (mixed currencies cannot be summed).
- The report uses `safe_abs` from frappe.utils which was added to handle edge cases in absolute value calculations.
