# Search & Filters

## Summary
Extensive customizations to item search queries, list view filters, report filters, link field filters, and company-based filtering across doctypes. Key additions include department-based item filtering, child company item restrictions, custom UOM search with packaging support, multi-select filters, bank clearance company filters, and real-time company filters on financial reports.

## Commits

### Core Query Refactoring (2022)
| Hash | Message | Date |
|------|---------|------|
| 797512ca13 | fix: Company bank account filter in Bank Clearance | 2022-10-26 |
| 2f145f9912 | refactor: rewrite query in QB | 2022-11-05 |
| 60af9c0516 | fix: Create POS Opening Entry POS Profile filter | 2022-11-04 |
| f7204daf92 | AddFiltered | 2022-11-07 |
| 37bed12df4 | fix: Project filter in timesheet | 2022-11-07 |
| 8a01da3b9e | chore: Remove raw SQL query | 2022-11-12 |
| 4c0b5ceb9e | refactor: search queries (backport #33004) | 2022-11-17 |
| 7751870e48 | PRItemsFilter | 2022-12-14 |
| b19abf0331 | MRfilterInPO | 2022-12-05 |

### Item Name & Filters (2023)
| Hash | Message | Date |
|------|---------|------|
| 345c78dda8 | itemnameFilter | 2023-04-20 |
| 68750fdba6 | add filter month | 2023-09-07 |
| b0d5ee1197 | feat filter account based on mapping | 2023-09-27 |
| 14939c42c8 | default value filter if missing | 2023-09-19 |
| cfa600294e | set query stock item | 2023-10-13 |
| bb4f9a1c52 | add filter to month | 2023-11-06 |
| 7f4ab6f69e | set bold on filter | 2023-12-04 |

### Custom Filters & Search Function (2024)
| Hash | Message | Date |
|------|---------|------|
| b19de62f3e | realtime company filters | 2024-03-25 |
| 5ef4bcf30a | add filters custom | 2024-05-17 |
| c481432ac6 | add search function | 2024-07-22 |
| 2a5187d677 | add filter to items | 2024-07-25 |
| 7b4b3522eb | add filters to item and adjust workstation view | 2024-08-13 |
| 86923164a2 | add filters to stock recon | 2024-08-29 |
| 9b27ebc526 | add filter on pop up | 2024-08-20 |
| ed956c36d3 | add JS filter | 2024-10-28 |
| 929b22eb94 | add filter condition | 2024-10-28 |

### Report & List View Filters (2025)
| Hash | Message | Date |
|------|---------|------|
| 5c71e57971 | auto filter GL based on click | 2025-05-14 |
| 049afe5094 | add income account filter | 2025-07-02 |
| 987448fcb5 | add filter PO | 2025-07-07 |
| 8486337c2a | remove return filters | 2025-08-14 |
| 677258026c | [feat] add filter company | 2025-11-19 |
| 95d265cac6 | uob: add filter bank account only for UOB | 2025-11-13 |
| c4f8fd6c62 | prod: add filter detail | 2025-11-27 |
| 6b5730f378 | switch view filters | 2025-12-29 |

### Recent Filter Additions (2026)
| Hash | Message | Date |
|------|---------|------|
| 3e05de7feb | add internal filter on list view | 2026-01-22 |
| 9b5f260eb8 | filter material request for sub company | 2026-01-22 |
| 786db7f50d | add list view filter for PR | 2026-03-12 |
| b2c24b28ba | filter tax template | 2026-04-15 |
| bd1396bdfb | add filter company on bank clearance | 2026-05-12 |
| 5f1027ea56 | multi select the filter item | 2026-06-25 |
| f4fd5ee188 | search card | 2026-06-25 |
| cddaf83420 | add filter only month, and fix another issue | 2026-07-23 |

... and 55 more commits

## Affected Files

**Core Query Engine:**
- erpnext/controllers/queries.py
- erpnext/stock/get_item_details.py
- erpnext/public/js/utils.js

**List View Filters (JS):**
- erpnext/stock/doctype/material_request/material_request.js
- erpnext/stock/doctype/delivery_note/delivery_note.js
- erpnext/stock/doctype/purchase_receipt/purchase_receipt.json
- erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.js
- erpnext/buying/doctype/purchase_order/purchase_order.js
- erpnext/buying/doctype/request/request.js
- erpnext/selling/doctype/sales_order/sales_order.js
- erpnext/accounts/doctype/sales_invoice/sales_invoice.js
- erpnext/accounts/doctype/bank_clearance/bank_clearance.js
- erpnext/manufacturing/doctype/workstation/workstation.js

**Report Filters:**
- erpnext/accounts/report/general_ledger/general_ledger.js
- erpnext/accounts/report/general_ledger/general_ledger.py
- erpnext/accounts/report/asset_depreciations_and_balances/asset_depreciations_and_balances.js
- erpnext/foms/report/batch_delivery/batch_delivery.js
- erpnext/foms/report/delivery_note_analysis/delivery_note_analysis.js
- erpnext/foms/report/picking_list_report/picking_list_report.js
- erpnext/manufacturing/report/cos_product_variances/cos_product_variances.js
- erpnext/gp_erp/report/budget_variance_greenphyto/budget_variance_greenphyto.js
- erpnext/public/js/financial_statements.js

**Scrap Request (Custom Doctype with filters):**
- erpnext/stock/doctype/scrap_request/scrap_request.js
- erpnext/stock/doctype/scrap_request/scrap_request.py

**UOB Payment Filters:**
- erpnext/uob/doctype/payment_approval/payment_approval.js
- erpnext/uob/page/payment_bulk_approval/payment_bulk_approval.js

## Flow/Logic

### Item Query (controllers/queries.py - `item_query`)
1. Builds search conditions from meta search_fields plus item_code, item_group, item_name
2. **Party-specific filtering**: If customer/supplier filter passed, fetches Party Specific Item rules and restricts results to allowed items
3. **Department filtering**: If `department` filter passed, queries Item Department child table to get list of items belonging to that department, then filters by `name IN (item_list)`
4. **Child company restriction**: If current company has a `parent_company`, automatically adds filter `item_group != 'Raw Material'` to hide raw materials from sub-companies
5. **Description search**: Only scans description field if total item count < 50,000 (performance guard)
6. **Barcode search**: Includes items matching barcode via subquery on Item Barcode child table
7. Results ordered by position of search text in name/item_name (relevance ranking)

### UOM Query (controllers/queries.py - `uom`)
1. Custom UOM search that joins UOM with UOM Conversion Detail
2. When `is_packaging` filter is set, includes both packaging and carton UOMs
3. Groups by UOM name to avoid duplicates from multiple conversion rows

### Company-Based Filters
1. **Real-time company filters**: Company filter applied dynamically on list views, persists across navigation
2. **Bank Clearance**: Filters bank accounts to show only those belonging to selected company
3. **Material Request for sub-company**: Restricts MR list to current sub-company's documents
4. **Financial reports**: Company filter on GL, P&L, Balance Sheet determines which accounts/entries are shown

### List View Filter Pattern
1. Standard pattern: Add `onload` or `setup` handler in doctype JS file
2. Sets `frm.fields_dict.fieldname.get_query` for link fields
3. Or uses `frappe.listview_settings[doctype].filters` for default list filters
4. Some filters use `set_query` with dynamic conditions based on other field values

### General Ledger Auto-Filter
1. Clicking on account in financial statements auto-navigates to GL report with account pre-filtered
2. `auto filter GL based on click` enables drill-down from summary reports to detailed GL entries

### Search Card
1. Custom search card UI component for quick item lookup
2. Multi-select filter support for item fields (added 2026-06-25)

### Report Filter Enhancements
1. Month-only filter option for date-based reports (avoids full date picker)
2. Account-based mapping filter: filters accounts based on configured account mappings
3. Default filter values set when filters are missing/empty (prevents blank report runs)
4. Filter bold styling for required/important filters

### POS Query Fix
1. Cast POS query inputs to integers to prevent SQL type mismatch errors
2. POS Profile filter respects company context in Opening Entry

## Dependencies
- Item Department (child doctype for department-item linking)
- Party Specific Item (standard ERPNext feature, used in item_query)
- Company hierarchy (parent_company field for child company detection)
- Part Number Settings (account mapping used in filter context)
- UOM Conversion Detail (is_packaging, is_carton flags)
- Financial Statements JS (shared filter logic for all financial reports)

## Notes
- Child companies automatically cannot see Raw Material items in item link fields - this is enforced at query level
- Department filter returns empty placeholder `["000"]` if no items found for department, preventing unfiltered results
- Item search performance: description search disabled above 50k items to maintain query speed
- `get_filters_cond` and `get_match_cond` are standard frappe utilities used throughout; GP customizations add conditions on top
- Multi-select filters (2026) allow selecting multiple items in a single filter field
- Bank account filters for UOB are bank-type specific (only show UOB accounts in UOB payment flows)
- Real-time company filter (2024-03-25) ensures all list views respect currently selected company without page reload
- Return document filters can be toggled on/off for cleaner list views
