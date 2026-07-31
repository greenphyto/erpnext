# PL Performance Review Report

## Summary
A Profit & Loss performance review report with YTD and Monthly periodicity modes, budget comparison, prior year comparison, and ratio rows (GOP%, Payroll Cost%).

## Commits
| Hash | Message | Date |
|------|---------|------|
| a2eb113269 | fixing PL performance report | 2026-07-22 |
| 2325ffd527 | report PL performance init | 2026-07-22 |

## Affected Files
- erpnext/gp_erp/report/p&l_performance_review/__init__.py
- erpnext/gp_erp/report/p&l_performance_review/p&l_performance_review.js
- erpnext/gp_erp/report/p&l_performance_review/p&l_performance_review.json
- erpnext/gp_erp/report/p&l_performance_review/p&l_performance_review.py

## Flow/Logic
1. **Filters** (JS):
   - Company (required), Year/Fiscal Year (required), Periodicity (YTD or Monthly), Month (to_month), Cost Center (MultiSelectList), Currency, Accumulated Values (Check), Hide Zero Balance (Check).

2. **Filter Processing** (`control_filters`):
   - Determines `view_mode` (YTD or Monthly).
   - Sets `period_start_date` (Jan 1) and `period_end_date` (last day of selected month).
   - For Monthly mode, forces `accumulated_values=0` internally (GL fetch always net-per-month) while preserving `display_accumulated` for presentation.

3. **Data Fetch** (`fetch_pl`):
   - Uses standard `get_data()` from `erpnext.accounts.report.financial_statements` for Income and Expense root types.
   - Passes `accumulated_values`, `ignore_closing_entries=True`, cost center filters.

4. **Budget Integration**:
   - Calls `get_budget_data()` and `add_budget_to_rows()` from `budget_variance_greenphyto` report.
   - Adds `_budget` columns per period and `budget_ytd` / `total_actual` summary columns via `add_summary_columns()`.

5. **Prior Year Comparison** (`merge_prior_year`):
   - Fetches previous fiscal year's P&L data using same parameters shifted back one year.
   - Merges into current rows as `prior_total`, `prior_var_amount`, `prior_var_percent`.
   - Matches rows by `account_origin` or `account` key.

6. **Net Profit/Loss**:
   - Computed via `get_net_profit_loss()` (Income total - Expense total).
   - Prior year values applied via `apply_prior_to_net()`.

7. **Ratio Rows** (`append_ratio_rows`):
   - **GOP %**: Profit / Total Revenue * 100 for each summary field and period.
   - **Payroll Cost %**: Payroll account (account_number "600001") total / Total Revenue * 100.
   - `get_payroll_values()` queries GL entries for payroll account descendants, computes per-period and budget values.

8. **Display Modes**:
   - **YTD**: Shows single Actual YTD, Budget YTD, and prior year columns. Fields remapped via `remap_ytd_fields()`.
   - **Monthly**: Shows the selected month column + budget column, plus summary columns (Total Actual, Budget YTD, Prior Year).
   - When "Accumulated Values" is ON in Monthly mode, `apply_display_accumulation()` replaces single-month column with cumulative Jan..to_month total.
   - When OFF, `strip_ytd_to_month()` ensures summary totals reflect only the displayed month for like-to-like variance.

9. **Formatting** (JS `formatter`):
   - Ratio rows display as percentage with 2 decimals (skipping currency formatter).
   - Bold styling for group rows, profit row, and ratio rows.
   - Negative values shown in red (`text-danger`).
   - Tree view with `initial_depth: 3`.

10. **Columns** (`get_report_columns`):
    - Account (tree link), Acc. Code, Currency (hidden).
    - Monthly mode: period actual + budget per month, Total Actual, Budget YTD, Prior Year actual, Prior Year variance ($ and %).
    - YTD mode: Actual YTD, Budget YTD, Act vs Budget variance, Prior Year actual, Prior Year variance.

## Dependencies
- erpnext.accounts.report.financial_statements (get_data, get_period_list)
- erpnext.gp_erp.report.budget_variance_greenphyto (budget functions)
- erpnext.accounts.utils (get_fiscal_year)
- GL Entry table
- Budget doctype
- Account tree (for payroll account_number lookup)

## Notes
- Payroll account is hardcoded as account_number "600001".
- The report handles the accumulated/non-accumulated toggle carefully to ensure variance comparisons are like-to-like (single month vs single month, or YTD vs YTD).
- Prior year comparison uses fiscal year resolution; if prior FY doesn't exist, it silently skips.
- Column labels include short year strings (e.g., "'26", "'25") for compact display.
