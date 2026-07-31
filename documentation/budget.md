# Budget Variance Report & Validation

## Summary
Monthly budget variance report that compares actual GL balances against budgeted amounts per account per cost center. Includes a GP-custom "Budget Variance Greenphyto" report that integrates with the Profit & Loss financial statement structure, showing budget columns alongside actuals with variance calculations. Supports bulk upload/download of budget templates and multi-sheet XLSX export by cost center.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 33e1c44eb4 | enhance report formatting and alignment in financial statements and budget variance | 2026-06-25 |
| ad2b109f42 | fix syntax error in budget variance | 2026-06-03 |
| 3cc4fad21a | fix ytd filter on budget report | 2026-05-21 |
| f103e40afc | budget report with end date | 2026-05-05 |
| 6f2e8d3b92 | show all account budget on PL report | 2026-04-29 |
| c18ba5cd99 | disable formulas for budget | 2026-04-28 |
| 4e8fdbf841 | fixing budget variance report | 2026-04-27 |
| 7d757891b2 | fixing total and subtotal greenphyto budget | 2026-04-27 |
| 5c919218c1 | fix budget colom part on PL | 2026-04-24 |
| 12e2647b43 | disable report budget variance | 2026-04-24 |
| 26e4c1fd06 | budget variance report for greenphyto | 2026-04-22 |
| 311b166139 | fix chart for budget | 2026-04-10 |
| 8738312983 | calculate budget amount | 2026-04-10 |
| c5312d53a3 | add upload and download template budget | 2026-04-08 |
| 595aaad99d | fix: add translate function to string on budget_variance_report.js | 2022-10-25 |
| 16f364da37 | fix: add translate function to name of chart labels in budget_variance_report.py | 2022-10-25 |

## Affected Files
**GP Custom Budget Report**
- erpnext/gp_erp/report/budget_variance_greenphyto/budget_variance_greenphyto.py
- erpnext/gp_erp/report/budget_variance_greenphyto/budget_variance_greenphyto.js
- erpnext/gp_erp/report/budget_variance_greenphyto/budget_variance_greenphyto.json

**Standard Budget Variance Report**
- erpnext/accounts/report/budget_variance_report/budget_variance_report.py
- erpnext/accounts/report/budget_variance_report/budget_variance_report.js
- erpnext/accounts/report/budget_variance_report/budget_variance_report.json

**Budget Doctype**
- erpnext/accounts/doctype/budget/budget.py
- erpnext/accounts/doctype/budget/budget.js
- erpnext/accounts/doctype/budget/budget.json
- erpnext/accounts/doctype/budget/budget_upload_template.py
- erpnext/accounts/doctype/budget_account/budget_account.json

**Financial Statements Integration**
- erpnext/accounts/report/financial_statements.py
- erpnext/accounts/report/profit_and_loss_statement/profit_and_loss_statement.py
- erpnext/accounts/report/profit_and_loss_statement/profit_and_loss_statement.js
- erpnext/accounts/report/balance_sheet_v2/balance_sheet_v2.py

## Flow/Logic

### Budget Variance Greenphyto Report (Main GP Report)

1. **Filter Control** (`control_filters`):
   - Takes `year`, `month`, `to_month` from filters.
   - Computes `period_start_date` (first day of `month`) and `period_end_date` (last day of `to_month`).
   - Sets `from_fiscal_year` and `to_fiscal_year` to the selected year.

2. **Period List Generation**:
   - Uses `get_period_list` from financial_statements to build month-by-month periods.

3. **Account Filtering** (`get_budget_account`):
   - If `hide_zero_balance` is enabled, fetches only accounts that have a Budget entry for the selected cost center/company.
   - Queries `tabBudget Account` joined with `tabBudget` (docstatus=1).

4. **Actual Data**:
   - Calls `get_data` from financial_statements for Income (Credit) and Expense (Debit) root types.
   - Returns hierarchical account rows with period values from GL entries.

5. **Budget Data** (`get_budget_data`):
   - Fetches monthly budget amounts from `tabBudget Account` fields (january, february, ..., december).
   - Groups by account, summing across matching Budgets (same company, fiscal year, cost center).
   - Returns `budget_map`: `{account: {month_number: amount}}`.

6. **Add Budget to Rows** (`add_budget_to_rows`):
   - **First pass (leaf accounts)**: For each period, looks up the budget amount by month number. Stores as `{period.key}_budget`.
   - **Second pass (group accounts)**: Iterates in reverse, summing child account budgets into parent group rows.
   - Handles accumulated mode (running total) and yearly mode (sum selected month range).

7. **Summary Columns** (`add_summary_columns`):
   - `total_actual`: Sum of all period actual values.
   - `budget_ytd`: Sum of all period budget values.
   - `variance_amount`: `total_actual - budget_ytd`.
   - `variance_percent`: `(variance_amount / budget_ytd) * 100`.

8. **Net Profit/Loss** (`get_net_profit_loss`):
   - Calculates income - expense for each period (including budget columns).
   - Computes summary columns for the net profit row.

9. **Report Columns** (`get_report_column`):
   - Standard period columns (from financial_statements).
   - Appends: Total Actual, Budget YTD, Variance $, Variance % (labeled with month range).

10. **XLSX Export** (`export_with_cost_centers`):
    - Generates one sheet per non-group cost center.
    - Each sheet contains the full P&L with budget columns for that cost center.
    - Integrates with `add_formulas` from balance_sheet_v2 for Excel formula support.

### Standard Budget Variance Report

1. Fetches dimensions (Cost Centers/Projects) and budget target details.
2. Uses Monthly Distribution percentages to allocate annual budget to months.
3. Fetches actual GL entries per dimension/account/month.
4. Computes: Target (budget), Actual (GL), Variance (Target - Actual) per period.
5. Supports cumulative mode and multiple fiscal years.

### Budget Upload Template
- `budget_upload_template.py` provides download/upload of budget data in spreadsheet format for bulk editing of monthly amounts per account.

## Dependencies
- `erpnext.accounts.report.financial_statements` (get_data, get_columns, get_period_list)
- `erpnext.accounts.report.balance_sheet_v2.balance_sheet_v2` (add_formulas for XLSX)
- `erpnext.controllers.trends` (get_period_date_ranges, get_period_month_ranges)
- Budget Account child table with monthly fields (january through december)
- Monthly Distribution doctype (for standard report percentage allocation)

## Notes
- The GP report reads budget directly from monthly fields on Budget Account, bypassing the Monthly Distribution mechanism used by the standard report.
- Budget Account JSON has individual month fields (january, february, etc.) which is a GP customization over the standard single `budget_amount` field.
- The `hide_zero_balance` filter only shows accounts that have at least one Budget entry, reducing noise.
- Variance % uses simple division; when budget is zero, variance % is set to 0.
- The export function generates per-cost-center sheets; the first sheet shows "all" (no cost center filter).
- `show_number_group` filter controls whether account numbers are displayed in account names.
