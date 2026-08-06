# Stock Entry

## Summary
Custom stock entry purpose types, scrap request integration, material transfer validations, WIP operation cost tracking, asset conversion from inventory, and zero-rate stock entry checks.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 048817af41 | add zero rate stock entry check | 2026-05-06 |
| de1228eedf | load salvage from stock entry get items | 2026-02-12 |
| bfd614f1b1 | fixing validation stock entry | 2025-12-04 |
| e1f3ab4b36 | adjust stock entry from return materials | 2025-07-14 |
| ef3020e7a5 | delete stock entry if cancel repack salad | 2025-03-24 |
| 898a23094b | adjust stock entry column for work order | 2025-02-06 |
| b4f9075cc4 | validate stock entry | 2024-12-30 |
| 03c27099af | set expense to stock entry | 2024-12-30 |
| e81f45fe41 | fix issue stock entry | 2024-12-12 |
| 6dcfbd6f8b | validate new stock entry | 2024-12-09 |
| dd71259560 | fix stock entry | 2024-10-28 |
| 046294e769 | fix costs issue for non items in stock entry | 2024-10-25 |
| c7f42f6364 | create Stock Entry without item | 2024-10-18 |
| bbdd137456 | remove mandatory from stock entry | 2024-10-18 |
| ae6d37c7e8 | adjust type stock entry | 2024-10-10 |
| 87da4e41c4 | create stock entry with reff | 2024-10-10 |
| 31ded1ed01 | add stock entry type | 2024-10-10 |
| 320e1bd5d8 | fix reference stock entry | 2024-10-09 |
| 29a0a3d4bb | update stock entry type | 2024-10-01 |
| ceb0afcc38 | adjust stock entry type | 2024-09-30 |
| 754c4cb074 | copy stock entry type | 2024-09-30 |
| 241e1c5cb1 | switch stock entry type | 2024-09-26 |
| 72204494c7 | add more precision on stock entry | 2024-09-19 |
| 4707797070 | add additional cost in stock entry | 2024-08-13 |
| beef0510ee | chore: remove `debugger` from `stock_entry_list.js` | 2022-11-08 |
| 2c5a8c43f6 | fix: make `consumed_qty` editable when backflush based on Material Transfer | 2022-11-07 |
| 4035873295 | fix: Pass project to stock entry items | 2022-10-29 |

## Affected Files

### Core Stock Entry
- erpnext/stock/doctype/stock_entry/stock_entry.py
- erpnext/stock/doctype/stock_entry/stock_entry.js
- erpnext/stock/doctype/stock_entry/stock_entry.json
- erpnext/stock/doctype/stock_entry/stock_entry_list.js
- erpnext/stock/doctype/stock_entry_detail/stock_entry_detail.json
- erpnext/stock/doctype/stock_entry_type/stock_entry_type.json

### Related Doctypes
- erpnext/stock/doctype/scrap_request/scrap_request.py
- erpnext/stock/doctype/stock_ledger_entry/stock_ledger_entry.json

### Controllers
- erpnext/controllers/accounts_controller.py
- erpnext/controllers/stock_controller.py
- erpnext/controllers/erp_api.py
- erpnext/controllers/foms.py

### Manufacturing Integration
- erpnext/manufacturing/doctype/work_order/work_order.py
- erpnext/manufacturing/doctype/work_order/work_order.js
- erpnext/manufacturing/doctype/work_order/work_order.json

### Notifications
- erpnext/gp_erp/notification/missing_rate_stock_entry/
- erpnext/gp_erp/notification/missing_work_order_rate/

### Patches
- erpnext/patches/v14_0/modify_stock_entry_type.py
- erpnext/patches/v14_0/modify_stock_entry_type2.py

## Flow/Logic

### 1. Stock Entry Type View System
- Uses a `stock_entry_type_view` field that maps to the underlying `stock_entry_type` and `purpose`.
- `validate_purpose()` resolves the actual purpose from `Stock Entry Type` doctype: `self.stock_entry_type = frappe.get_value("Stock Entry Type", self.stock_entry_type_view, "purpose")`.
- Custom stock entry types include: Material Issue, Material Receipt, Material Transfer, Material Transfer for Manufacture, Manufacture, Repack, Send to Subcontractor, Material Consumption for Manufacture.

### 2. Material Receipt Supplier Validation
- `valdiate_from_supplier()`: Material Receipt purpose requires a `from_supplier` field to be set, enforcing supplier traceability for incoming stock.

### 3. Batch Splitting Validation
- `validate_batch_splitting()`: When enabled in Stock Settings (`block_batch_splitting_transaction`), prevents partial batch transfers.
- Exempts items with a `consignment_request` reference.
- Checks if `transfer_qty < batch_source_qty` and throws error if splitting is attempted.

### 4. Partial Issue Validation
- `validate_partially_issue()`: Prevents partial issuing of stock for Material Issue purpose.
- Exempts WIP warehouses and "Other Packaging" material group items.
- Ensures entire batch qty is issued at once (currently commented out in validate flow).

### 5. WIP Operation Cost Tracking
- `calculate_wip_operation_cost()`: Calculates additional costs from `wip_additional_costs` child table.
- Each cost row has exchange_rate support and calculates `base_amount = amount * exchange_rate`.
- Total stored in `total_wip_additional_costs`.

### 6. Cost Center Validation
- `validate_cost_center()`: Auto-sets cost center on items and additional costs by looking up the expense account's linked cost center via `get_cost_center_from_account()`.

### 7. Scrap Entry Cancellation Guard
- `validate_scrap_entry_from_work_order()`: When cancelling a Material Transfer for Manufacture, checks if a scrap Material Issue exists for the previous operation.
- Uses `get_previous_operation()` to find the preceding operation's scrap entry.
- Forces user to cancel scrap entries before the transfer entry.

### 8. Work Order Material Return Tracking
- `set_close_materials()`: When fg_completed_qty equals work order qty, marks the return work order's `material_returned` flag.
- Reverses the flag on cancellation.

### 9. Asset Conversion from Inventory (StockEntryAsset)
- `StockEntryAsset` mixin class handles "Conversion from Inventory to Fixed Asset" type.
- `validate_stock_entry_asset()`: Validates asset expense accounts and categories for each item.
- `create_asset_stock()`: On submit, creates asset Items for stock items that don't have an existing asset item mapping.
- Uses `asset_for_item` link on Item to track the relationship.

### 10. Zero Rate Stock Entry Check
- Notification "Missing rate Stock Entry" triggers when items have `basic_amount == 0`.
- Alerts specific users about potential missing valuation rates.

### 11. Submit Flow
- Updates stock ledger entries
- Updates serial numbers
- Updates work order progress
- Makes GL entries
- Reposts future SLE and GLE
- Creates asset records (if asset conversion type)
- Sets close materials flag on work order

## Dependencies
- Work Order module (manufacturing integration)
- Scrap Request module (scrap material flow)
- Stock Ledger Entry (valuation)
- Batch management (batch splitting controls)
- `controllers/foms.py` (get_wip_warehouse, get_previous_operation, get_operation_number)
- Consignment Request (exemption from batch splitting)

## Notes
- The `stock_entry_type_view` vs `stock_entry_type` pattern allows custom GP types while maintaining compatibility with standard ERPNext purposes.
- Material Receipt always requires a supplier (`from_supplier`) - this is a GP-specific validation not in standard ERPNext.
- The `validate_partially_issue` method is currently commented out in the validate chain but the code is retained.
- Batch splitting validation can be bypassed for consignment request items.
- WIP additional costs support multi-currency with exchange rate conversion.
