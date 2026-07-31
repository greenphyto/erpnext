# Financial Statements

## Summary
Custom financial statement reports including Balance Sheet V2 (with accumulated values, account codes, and formula export), Cash Flow Greenphyto (custom indirect method cash flow), consolidated financial statement enhancements (bold formatting, group highlighting), and shared utilities for formatting and presentation currency conversion.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 71d6fa721c | add bold to consolidate and cash flow | 2026-06-30 |
| 31f784623f | add highlight group to consolidate invoice | 2026-05-21 |
| f144410409 | fixing bug on consolidate invoice | 2026-05-20 |
| ccfdf7b24c | fixing bug on consolidate invoice | 2026-05-20 |
| 1ba19876e5 | fixing balance sheet formula | 2026-04-27 |
| 8ba2021c7e | fix financial statement | 2026-02-04 |
| 56592b025a | prod: fixing consolidated financial statement | 2025-10-29 |
| ee3c2fe431 | add trial balance different notif | 2025-10-20 |
| a5b2349bef | add account code to PL and Balance Sheet | 2025-05-09 |
| 0f806e1fd0 | no consolidate on stock entry | 2024-10-25 |
| 93a0311ca2 | fix rounding balance sheet | 2024-04-19 |
| ce2b6e340e | Revert "make precision balance sheet" | 2024-04-09 |
| 5f9d2d3cdb | make precision balance sheet | 2024-04-08 |
| 1ff941fd3f | continue cash flow | 2024-02-02 |
| c4c9497b31 | temporary cash flow for greenphyto | 2024-01-29 |
| db863e8a9b | init cash flow report | 2024-01-26 |
| e98c70d1f7 | apply to balance sheet | 2024-01-17 |
| f3e4ae63ae | mandatory balance sheet accumulated value | 2024-01-17 |
| bceae081fd | copy balance sheet report to V2 | 2024-01-17 |
| 5eb6e367b5 | format report like balance sheet | 2023-12-08 |
| 44a813111c | trial balance remove number trial balance | 2023-12-06 |

## Affected Files
**Balance Sheet V2:**
- erpnext/accounts/report/balance_sheet_v2/__init__.py
- erpnext/accounts/report/balance_sheet_v2/balance_sheet_v2.html
- erpnext/accounts/report/balance_sheet_v2/balance_sheet_v2.js
- erpnext/accounts/report/balance_sheet_v2/balance_sheet_v2.json
- erpnext/accounts/report/balance_sheet_v2/balance_sheet_v2.py

**Cash Flow Greenphyto:**
- erpnext/accounts/report/cash_flow_greenphyto/__init__.py
- erpnext/accounts/report/cash_flow_greenphyto/cash_flow_greenphyto.js
- erpnext/accounts/report/cash_flow_greenphyto/cash_flow_greenphyto.json
- erpnext/accounts/report/cash_flow_greenphyto/cash_flow_greenphyto.py

**Consolidated Financial Statement:**
- erpnext/accounts/report/consolidated_financial_statement/consolidated_financial_statement.js
- erpnext/accounts/report/consolidated_financial_statement/consolidated_financial_statement.py

**Shared/Core:**
- erpnext/accounts/report/financial_statements.py
- erpnext/accounts/report/balance_sheet/balance_sheet.py
- erpnext/accounts/report/cash_flow/cash_flow.py
- erpnext/accounts/report/profit_and_loss_statement/profit_and_loss_statement.js
- erpnext/accounts/report/profit_and_loss_statement/profit_and_loss_statement.py
- erpnext/accounts/report/trial_balance/trial_balance.js
- erpnext/accounts/report/trial_balance/trial_balance.py
- erpnext/accounts/report/utils.py
- erpnext/accounts/utils.py

**Other:**
- erpnext/controllers/erp.py
- erpnext/hooks.py
- erpnext/public/js/controllers/stock_controller.js

## Flow/Logic

### Balance Sheet V2
1. Copied from standard Balance Sheet report with GP-specific enhancements.
2. `execute(filters)` calls `get_period_list()` from `financial_statements.py` with support for custom periodicities ("Single Month", "Multi Month").
3. Fetches Asset, Liability, and Equity data using `get_data()` with `accumulated_values` flag (defaults to 1).
4. Supports `monthly_net` filter: if periodicity is Monthly and `monthly_net` is set, forces non-accumulated values.
5. Computes provisional profit/loss and adds it to equity section.
6. Uses `convert_wrap_report_data()` from `report/utils.py` for presentation currency conversion.
7. `add_formulas()` function (registered in hooks `custom_export_report`) adds Excel formulas when exporting, allowing dynamic recalculation in spreadsheets.

### Cash Flow Greenphyto (Indirect Method)
1. Custom cash flow report using indirect method, specific to GPL company.
2. `CashFlowReport` class fetches P&L data and Balance Sheet data using existing report functions.
3. Hardcoded `ACCOUNT` dictionary maps logical categories (e.g., "Direct Income", "COGS", "Cash in Bank") to specific GPL account names.
4. Calculates:
   - Operating Activities: Net profit + depreciation + working capital changes (receivables, payables, accruals)
   - Investing Activities: Changes in fixed assets, investments
   - Financing Activities: Changes in loans, lease liabilities, share capital
5. Each section computes current period vs prior period balance differences.

### Consolidated Financial Statement
1. Fetches data across multiple companies for group reporting.
2. Supports Balance Sheet, Profit and Loss, and Cash Flow report types.
3. `get_companies()` retrieves subsidiary companies based on filters.
4. Bold formatting and group highlighting added for parent account rows to improve readability.
5. Stock entries excluded from consolidation (`no consolidate on stock entry`).

### financial_statements.py (Shared)
1. `get_period_list()` extended with:
   - `month` and `to_month` parameters for single/multi month filtering within a fiscal year.
   - "Single Month" and "Multi Month" periodicity options (both map to 12-month iteration internally).
2. Account code display: account numbers prepended to account names in report output.
3. Trial balance notification: `trial_balance_different_issue()` scheduled monthly to detect discrepancies.

## Dependencies
- `erpnext.accounts.report.financial_statements` (core period/data functions)
- `erpnext.accounts.report.utils` (convert_to_presentation_currency, convert_wrap_report_data)
- `erpnext.accounts.utils` (get_fiscal_year, remove_account_number)
- hooks.py `custom_export_report` for Excel formula injection
- hooks.py `scheduler_events.monthly` for trial balance notification

## Notes
- Balance Sheet V2 defaults to accumulated values (unlike standard which may default to non-accumulated for Monthly).
- The Cash Flow Greenphyto report is hardcoded to GPL company accounts. Adding a new company requires updating the `ACCOUNT` dictionary.
- `custom_export_report` hook injects formulas into Balance Sheet, P&L, and Consolidated reports when exported to Excel.
- Rounding precision was attempted (`make precision balance sheet`) then reverted; current behavior uses default Frappe precision.
- The `ignore_closing_entries` filter passes through to GL Entry queries, controlling whether period closing vouchers are included.
