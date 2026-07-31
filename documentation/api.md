# API

## Summary
Custom REST API endpoints in `erp_api.py` serving as the bridge between ERPNext and FOMS (Factory Operations Management System). Provides endpoints for work order management, stock operations, BOM creation, material requests, delivery orders, finish goods, lead time queries, and LOT ID data retrieval.

## Commits
| Hash | Message | Date |
|------|---------|------|
| e6178b40b0 | get lead time API | 2026-07-01 |
| c1e1a4bdc1 | skip restrict for CEO | 2026-03-17 |
| a74794c043 | endpoint get LOT ID data | 2026-01-21 |
| 380a926c61 | add company parameter to erp endpoint | 2025-12-23 |
| 9f5b33b90a | create endpoint information | 2025-11-06 |
| c0a004f144 | download file on api | 2025-04-25 |
| 628c6b9b01 | check overlaping value | 2024-09-23 |
| a7ea41a387 | update api json | 2024-09-05 |
| 73fbb77f70 | apply workflow to material request api | 2024-09-04 |
| 0e5c750ccf | change API | 2024-09-04 |
| 1bd79f9fbc | add to api wrapper | 2024-08-22 |
| 4ef62af7a7 | update API for finish goods | 2024-07-29 |
| 971b1f8e39 | add api endpoint for update request | 2024-07-04 |
| a5f601accf | add api endpoint | 2024-07-02 |
| 1ae428de6b | add api for request | 2024-06-26 |
| 936dc75b91 | add endpoint for mat. receipt | 2024-05-20 |
| 91342d919a | backup api if main api failed | 2023-11-03 |

## Affected Files
**Core API:**
- erpnext/controllers/erp_api.py
- erpnext/controllers/erp.py
- erpnext/controllers/foms.py
- erpnext/controllers/uob.py

**Supporting Doctypes:**
- erpnext/accounts/doctype/material_group/material_group.py
- erpnext/buying/doctype/request/request.json
- erpnext/buying/doctype/request/request.py
- erpnext/buying/doctype/request_items/request_items.json
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.js
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.json
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.py

**Other:**
- erpnext/patches/v14_0/fix_part_number.py
- erpnext/setup/utils.py
- erpnext/stock/doctype/stock_entry/stock_entry.json
- erpnext/uob/doctype/uob_integration_settings/uob_integration_settings.py
- erpnext/www/swagger/api.json

## Flow/Logic

### API Architecture
1. All endpoints are in `erp_api.py` decorated with `@frappe.whitelist()`.
2. Input data is parsed via `get_data()` helper that handles both JSON strings and dicts.
3. Every API call logs to `FOMS Data Mapping` via `save_log()` for traceability.
4. Results are logged back via `update_log()` linking the created document.
5. Multi-company support: `company` parameter added to endpoints; defaults to `erpnext.get_default_company()`.
6. `switch_to_company_admin(company)` sets session context to the company's admin user for permission handling.

### Key Endpoints

#### `create_bom(data)`
- Creates BOM from FOMS product data.
- Resolves item by `foms_product_id`.
- Delegates to `create_bom_products()` in `controllers/foms.py`.

#### `create_work_order(fomsWorkOrderID, fomsLotID, productID, salesOrderNo, qty, gross_weight, uom, submit, company)`
- Creates Work Order from FOMS work order data.
- Resolves item by `foms_product_id`, finds active BOM.
- Calls `_create_work_order()` with rate_from_bom disabled.
- Returns ERPWorkOrderID and ERPBOMId.

#### `start_work_order(erpWorkOrderID)`
- Transfers materials for manufacturing.
- Calculates pending transfer qty: `doc.qty - doc.material_transferred_for_manufacturing`.
- Creates and submits Material Transfer Stock Entry.

#### `update_qty_after_finish(erpWorkOrderID, batch_id, new_qty, submit, posting_date, posting_time, remark)`
- Creates Stock Reconciliation to adjust finished goods qty.
- Uses Manufacturing Settings default FG warehouse.
- Links to work order via `reff_id` field.

#### `update_item_safety_stock(item_code, safety_stock, company)`
- Updates Item.safety_stock value.
- Syncs with Item Reorder table: updates existing reorder level or creates new row.
- New reorder rows auto-set `warehouse_reorder_qty` to 2x the safety stock or last purchase receipt qty.
- Resolves PIC (Person In Charge) from Part Number Details.

#### `get_lead_time_by_custom_names` (imported from request.py)
- Returns lead time data for items based on custom naming.

#### LOT ID Data Endpoint
- Retrieves LOT-specific manufacturing data for FOMS tracking.

### Data Logging (FOMS Data Mapping)
1. `save_log(doctype, data_name, raw_data, reopen, now, endpoint)` enqueues log creation.
2. `update_log(doctype, data_name, result_doctype, result, now, name_id)` links created document to log.
3. `make_in_progress` marks log as being processed.
4. If `frappe.conf.testing_site` is set, operations run synchronously (`now=1`).

### UOM/Item Override System
1. `get_item_overide()` reads FOMS Integration Settings `item_conversion` table.
2. Maps FOMS items to ERPNext items with conversion factors.
3. `get_uom_overide()` maps (item_code, from_uom) to target UOM with conversion factor.
4. Used during work order and stock entry creation to handle unit mismatches.

### Scheduler-Based Processing
1. `run_pending_harvesting_transfer` (every 5 min): processes queued harvesting transfers.
2. `run_pending_harvesting` (every 5 min): processes queued harvesting completions.
3. Handles async operations that may fail and need retry.

## Dependencies
- `erpnext.controllers.foms` (core FOMS business logic: create_work_order, create_bom_products, etc.)
- `erpnext.foms.doctype.foms_data_mapping` (logging/audit trail)
- `erpnext.foms.doctype.foms_integration_settings` (configuration: auto_submit flags, UOM/item mappings)
- `erpnext.manufacturing.doctype.work_order.work_order` (make_stock_entry)
- `erpnext.manufacturing.doctype.job_card.job_card` (make_stock_entry, make_time_log)
- `erpnext.stock.doctype.batch.batch` (get_batch_no, get_available_batch, get_batch_qty, make_batch)
- `erpnext.buying.doctype.request.request` (forecast settings, lead time)
- `erpnext.setup.doctype.company.company` (switch_to_company_admin)

## Notes
- `PRECISION_FACTOR = 4` and `STOCK_TOLERANCE = 0.001` are constants used for qty comparisons to handle floating point issues.
- The `backup api if main api failed` commit indicates a fallback mechanism when primary FOMS API calls fail.
- CEO role skips restriction checks (`skip restrict for CEO`) allowing full API access regardless of company/user filters.
- Swagger documentation available at `erpnext/www/swagger/api.json`.
- All API endpoints use `ignore_permissions=True` for document creation since permission is handled at the API authentication layer.
