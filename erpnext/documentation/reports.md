# Reports

## Summary
Various custom reports for GP ERPNext covering financial statements (Balance Sheet V2, P&L), stock reports (stock ledger with account code), sales/invoice reports (invoice listing, GST return summary), WIP account detail, trade debtors/creditors, asset depreciation, picking list, delivery note analysis, and cost of sales product variances.

## Commits
| Hash | Message | Date |
|------|---------|------|
| b5fe8232ff | fix issues report and supplier | 2026-07-21 |
| 1e178764b9 | increase report column length | 2026-06-22 |
| 7d275c3364 | Revert "disable brackets for all report" | 2026-05-13 |
| 2fdb940d04 | disable brackets for all report | 2026-05-11 |
| 498a17e651 | fix total report | 2026-05-07 |
| 438d86bef6 | add account code to Stock Ledger report | 2026-04-28 |
| 54b97cdd34 | fix export report | 2026-04-24 |
| 3611d6e76b | add total to sub-group PL report | 2026-04-22 |
| 73cab2d0e2 | add donor report list | 2026-02-26 |
| 79fd99e022 | fix invoice report | 2026-02-04 |
| eacda9989f | update picking list report with draft filter | 2026-01-26 |
| 80a5202b35 | fix precision GST report | 2026-01-21 |
| 0eb8671c98 | fix GST report | 2026-01-20 |
| 417d593078 | fix trade creditor report | 2026-01-20 |
| 68d9737606 | add report column, WIP | 2025-12-31 |
| 04bd3b83ec | init report picking list report | 2025-12-29 |
| ba90abbd63 | adjust wip report data | 2025-12-23 |
| 74d12958ba | add qty to WIP report | 2025-12-18 |
| 08f94ec128 | init WIP report | 2025-12-18 |
| 75682c62fe | prod: add item row taxes in GST report | 2025-12-04 |

## Affected Files

**Financial Statements**
- erpnext/accounts/report/balance_sheet/balance_sheet.py
- erpnext/accounts/report/balance_sheet_v2/balance_sheet_v2.py
- erpnext/accounts/report/profit_and_loss_statement/profit_and_loss_statement.py
- erpnext/accounts/report/consolidated_financial_statement/consolidated_financial_statement.py
- erpnext/accounts/report/financial_statements.py
- erpnext/public/js/financial_statements.js

**Invoice & Sales Reports**
- erpnext/foms/report/invoice_listing_details/invoice_listing_details.py
- erpnext/foms/report/sales_invoice_price/sales_invoice_price.py
- erpnext/accounts/report/sales_register/sales_register.py
- erpnext/accounts/report/purchase_register/purchase_register.py

**GST Reports**
- erpnext/accounts/report/gst_return_summary_report/gst_return_summary_report.py
- erpnext/accounts/report/gst_return_summary_report/gst_return_summary_report.js
- erpnext/accounts/report/sales_taxes/sales_taxes.py
- erpnext/accounts/report/purchase_taxes/purchase_taxes.py

**Trade Debtors/Creditors**
- erpnext/accounts/report/trade_debtors/trade_debtors.py
- erpnext/accounts/report/trade_debtors_summary/trade_debtors_summary.py
- erpnext/accounts/report/trade_creditors/trade_creditors.js
- erpnext/accounts/report/trade_creditors/trade_creditors.json

**WIP Account**
- erpnext/foms/report/wip_account_detail/wip_account_detail.py
- erpnext/foms/report/wip_account_detail/wip_account_detail.js
- erpnext/foms/report/wip_account_detail/wip_account_detail.json

**Picking List**
- erpnext/foms/report/picking_list_report/picking_list_report.py
- erpnext/foms/report/picking_list_report/picking_list_report.js

**Delivery & Distribution**
- erpnext/foms/report/delivery_note_analysis/delivery_note_analysis.py
- erpnext/foms/report/distribution_by_stores/distribution_by_stores.py
- erpnext/foms/report/product_sold_by_customer/product_sold_by_customer.py
- erpnext/foms/report/product_sold_by_customer_(in_kg)/product_sold_by_customer_(in_kg).py
- erpnext/foms/report/product_returns/product_returns.py

**Work Order & Manufacturing**
- erpnext/foms/report/work_order_costs/work_order_costs.py
- erpnext/foms/report/work_order_operations_detail/work_order_operations_detail.py
- erpnext/manufacturing/report/cos_product_variances/cos_product_variances.py

**Asset Reports**
- erpnext/accounts/report/asset_depreciations_and_balances/asset_depreciations_and_balances.py
- erpnext/accounts/report/asset_depreciations_and_balances/report_new.py
- erpnext/assets/report/asset_depreciation_amount/asset_depreciation_amount.json

**Stock Reports**
- erpnext/stock/report/stock_ledger/stock_ledger.py
- erpnext/stock/report/stock_balance/stock_balance.json
- erpnext/stock/report/product_bundle_balance/product_bundle_balance.py
- erpnext/stock/report/itemwise_recommended_reorder_level/itemwise_recommended_reorder_level.py

**Other Custom Reports**
- erpnext/foms/report/donor_status/donor_status.py
- erpnext/accounts/report/journal_entry_list/journal_entry_list.py
- erpnext/accounts/report/part_number/part_number.py
- erpnext/accounts/report/statement_of_account_(outstanding)/statement_of_account_(outstanding).py
- erpnext/gp_erp/report/budget_variance_greenphyto/budget_variance_greenphyto.py
- erpnext/accounts/report/cash_flow_greenphyto/cash_flow_greenphyto.py

## Flow/Logic

### WIP Account Detail Report
1. Gets WIP accounts from Company's `operation_wip_account` child table (excludes Harvesting).
2. Queries GL Entry joined with Stock Entry and Work Order to sum debit-credit per work order per WIP account.
3. Adds Journal Entry amounts referencing Work Orders to the totals.
4. Fetches the latest Sales Invoice price per item (using `ROW_NUMBER() OVER PARTITION BY item_code ORDER BY posting_date DESC`) as the MAP price.
5. Calculates `total_amount = qty * map_price` for comparison against WIP value.
6. Groups output by account in operation order (Seeding, Transplanting, then others) with subtotals per group.
7. Filters: company, work_order, item_code, posting_date (cutoff), operation, price_source.

### Invoice Listing Details Report
1. Joins Sales Invoice with items, taxes, address, delivery note, and stock ledger entry (for COS valuation rate).
2. Calculates per-item GST amount proportionally: `item_amount / invoice_total * total_gst_amount`.
3. Shows both invoiced items and un-invoiced delivery note items (DN items without matching SI detail).
4. Includes deleted invoices from `tabDeleted Document` for audit trail.
5. Outputs: invoice date, invoice no, status, customer, store name, PO, delivery note, item, qty, UOM, weight, COS, price, amount, GST, total.
6. Appends TOTAL rows for each section (invoiced, un-invoiced, deleted).

### Balance Sheet V2 / Profit & Loss
1. Custom `balance_sheet_v2.py` extends standard financial statement logic.
2. Adds sub-group totals to P&L report (`add total to sub-group PL report`).
3. Bracket display for negative values can be toggled (added then reverted).
4. `financial_statements.py` modified for custom grouping and formatting.
5. `financial_statements.js` customizes client-side rendering.

### GST Return Summary Report
1. Calculates GST from Sales/Purchase Invoice taxes with item-level tax rate breakdown.
2. Handles precision issues (`fix precision GST report`).
3. Per-item tax rates from `item_tax_rate` JSON field are parsed and applied.
4. Supports filtering by date range, company, and tax type.

### Stock Ledger Report Enhancement
1. Added `account_code` column to stock ledger report.
2. Links stock movements to their corresponding GL account for reconciliation.

### Picking List Report
1. Shows items to be picked from warehouses for pending orders.
2. Supports draft filter to include/exclude draft pick lists.
3. Groups by delivery date and customer.

### Trade Debtors/Creditors
1. Custom aging reports for receivables and payables.
2. Trade creditors report fixed for correct outstanding calculation.
3. Trade debtors summary provides aggregated view per customer.

### Asset Depreciation Report
1. `report_new.py` provides an alternative asset depreciation and balances view.
2. Groups by asset category with purchase/disposal/depreciation summaries.
3. Works with the custom grouped depreciation JE structure.

### COS Product Variances
1. Compares actual production costs against standard/expected costs.
2. Breaks down variances by cost component (material, labor, overhead).
3. Uses work order and stock entry data for actual cost calculation.

### Donor Status Report
1. Tracks donation-related deliveries and their status.
2. Added donor report list functionality.

### Work Order Costs Report
1. Aggregates all costs associated with work orders.
2. Includes material costs, additional costs (electricity, wages, machinery, consumables).
3. Links to production variance journal entries.

## Dependencies
- Company (WIP accounts, cost centers, currency)
- GL Entry (primary data source for financial reports)
- Stock Ledger Entry (valuation rates, batch tracking)
- Sales Invoice / Purchase Invoice (revenue/expense data)
- Work Order / Stock Entry (manufacturing cost data)
- Delivery Note (fulfillment data)
- Packaging doctype (weight/UOM conversions)
- Address (outlet/store name for invoice listing)
- Rate Card (item pricing for WIP comparison)

## Notes
- The WIP report uses `HAVING ABS(SUM(gl.debit - gl.credit)) > 0.0001` to filter out fully cleared WIP entries.
- Invoice listing joins SLE for COS (Cost of Sales) using `voucher_detail_no` as the link key between Delivery Note Item and Stock Ledger Entry.
- Financial statement reports use `public/js/financial_statements.js` for client-side tree rendering and formatting.
- Export report fixes address formatting and column width issues for Excel/PDF generation.
- The bracket display for negative values was added then reverted - currently positive display is used.
- GST rate is typically 9% (Singapore GST) - hardcoded default in tax templates.
- Product sold by customer reports have two variants: one in standard UOM and one specifically in KG.
- Budget variance report (`budget_variance_greenphyto.py`) is a company-specific variant of the standard budget report.
