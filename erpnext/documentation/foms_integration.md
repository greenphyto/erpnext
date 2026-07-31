# FOMS Integration

## Summary
FOMS (Factory Order Management System) integration providing bidirectional data sync between ERPNext and FOMS. Covers item sync (raw materials & products), order sync (sales orders, forecasts), UOM conversion mapping, work order operations, delivery notes, and BOM/recipe synchronization.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 0408598071 | fetch foms try amount | 2026-06-26 |
| 9c2b1e57e2 | sync item from ERP to FOMS | 2026-05-08 |
| 9dac54f423 | remove debugging foms status | 2026-05-07 |
| 7c36e5e1bb | Add FOMS status watch | 2026-05-07 |
| 9650f88b6c | partially complete for foms data mapping | 2026-03-11 |
| f36740c26c | partially complete for foms data mapping | 2026-03-11 |
| c311907999 | foms: init report work order operation details | 2025-12-11 |
| cf86260981 | foms: fix stock uom not sync | 2025-12-10 |
| 5679808fc0 | foms: update revised qty | 2025-12-04 |
| 5bd0fcdb17 | foms: endpoint to update work order result | 2025-12-03 |
| 8145a5fde5 | make raw data editable in foms data mapping | 2025-11-06 |
| 15b6e0e8b7 | Dont sync to foms checklist | 2025-10-15 |
| 05f5634047 | prod: get different compare with FOMS | 2025-10-06 |
| a1e8ce7f9f | prod; add foms materials status | 2025-10-06 |
| f6cc877d8d | enable sync FOMS only for production | 2025-07-23 |
| 0a2e2eced2 | clear foms id when submit | 2025-07-22 |
| e59bf1baa3 | fix no copy for FOMS id | 2025-07-17 |
| 2f1be48f84 | change editable FOMS ID on DN | 2025-05-14 |
| b723931d66 | add foms lot id on sync | 2025-03-24 |

## Affected Files
**Core Integration**
- erpnext/controllers/foms.py (main sync logic, FomsAPI class, all sync functions)
- erpnext/controllers/erp_api.py (whitelisted API endpoints called by FOMS)
- erpnext/foms/__init__.py

**FOMS Integration Settings**
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.json

**FOMS Data Mapping**
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.py
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.js
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.json

**UOM Conversion**
- erpnext/foms/doctype/uom_foms_convertion/uom_foms_convertion.json
- erpnext/foms/doctype/uom_foms_convertion/uom_foms_convertion.py
- erpnext/foms/doctype/uom_foms_overide_item/uom_foms_overide_item.json

**Work Order & Manufacturing**
- erpnext/manufacturing/doctype/work_order/work_order.py
- erpnext/manufacturing/doctype/work_order/work_order.js
- erpnext/manufacturing/doctype/work_order/work_order.json

**Sales & Delivery**
- erpnext/selling/doctype/sales_order/sales_order.json
- erpnext/selling/doctype/sales_order/sales_order.py
- erpnext/selling/doctype/customer/customer.py
- erpnext/stock/doctype/delivery_note/delivery_note.py
- erpnext/stock/doctype/delivery_note/delivery_note.json

**Items & Stock**
- erpnext/stock/doctype/item/item.py
- erpnext/stock/doctype/item/item.json
- erpnext/stock/doctype/batch/batch.json
- erpnext/stock/doctype/packaging/packaging.json
- erpnext/stock/doctype/warehouse/warehouse.json

**Reports**
- erpnext/foms/report/foms_raw_material_status/foms_raw_material_status.py
- erpnext/foms/report/work_order_operations_detail/work_order_operations_detail.py

**Batch FOMS Page**
- erpnext/stock/dashboard/batch_foms_list.html
- erpnext/stock/page/batch_foms_details/batch_foms_details.js

## Flow/Logic

### FomsAPI Class (Authentication & Communication)
1. Instantiates with FOMS Integration Settings (URL, user, password).
2. `get_login()` authenticates via `/api/TokenAuth/Authenticate` and stores Bearer token.
3. `req(method, endpoint, data, params)` makes authenticated requests to FOMS API.
4. `convert_data()` recursively replaces None with empty strings (FOMS requirement).
5. `update_log()` writes request/response details to Sync Log for traceability.

### Item Sync (Raw Materials - GET from FOMS)
1. `get_raw_material()` calls FOMS `/RawMaterial/GetAllRawMaterial` API.
2. For each raw material, `create_raw_material()` either creates or updates an ERPNext Item.
3. Sets item group to "Raw Material", configures batch tracking, shelf life, FIFO valuation.
4. Stores `foms_raw_id` on the Item for cross-reference.
5. Assigns material group from FOMS category mapping.

### Item Sync (Products - GET from FOMS)
1. `get_products()` calls FOMS `/Product/GetAllProducts` API.
2. `create_products()` creates/updates Items with group "Products".
3. Sets `foms_product_id`, configures batch tracking and packaging.
4. Creates default workstation processes for each operation (Seeding, Transplanting, Harvesting).

### Item Sync (ERP to FOMS - POST)
1. `create_new_foms_item()` pushes items from ERP to FOMS.
2. Validates item belongs to allowed material groups.
3. Creates item category in FOMS if not exists (`create_item_category`).
4. Creates product variant type (`create_product_variant`).
5. Creates raw material record with safety stock, lead time, UOM.
6. Syncs available batches to FOMS after item creation.

### BOM/Recipe Sync (GET from FOMS)
1. `get_recipe()` fetches product recipes from FOMS per product.
2. `create_bom_products()` creates ERPNext BOMs from FOMS recipe data.
3. Maps FOMS process steps (PreHarvest, PostHarvest) to ERPNext operations.
4. Links raw materials to BOM items with correct UOM and qty.
5. Creates Workstation and Routing records if they don't exist.
6. Gets packaging info from FOMS and adds to item.

### Sales Order Sync (POST to FOMS)
1. On Sales Order submit, `update_foms_sales_order()` is triggered.
2. Skips non-stock items unless they are product bundles or salad orders.
3. Transforms SO items into FOMS format with product IDs, package IDs, weights.
4. Calls `create_customer_order` API with order type "One-off".
5. Stores returned `foms_id` and `req_id` back on the Sales Order.
6. On cancel, calls `cancel_sales_order` API.

### Request/Forecast Sync (POST to FOMS)
1. `update_foms_forecast()` syncs internal Request documents as forecasts.
2. Order type set to "Internal / Forecast" with delivery date range.
3. Maps department to FOMS department ID, sets day selection (Mon-Sun).
4. Similar item transformation as Sales Order but includes proposed customer.

### Delivery Note Sync (POST to FOMS)
1. `_sync_delivery_note2()` fires on DN submit.
2. Skips donations, giveaways, and non-stock items.
3. Sends delivery order details including item codes, batch numbers, warehouse, FOMS lot IDs.
4. On cancel, calls `cancel_delivery_note` API if FOMS ID exists.

### Work Order Operations (GET from FOMS + API endpoints)
1. FOMS calls `erp_api.create_work_order()` to create work orders in ERP.
2. FOMS calls `update_work_order_operation_status()` to report operation progress.
3. Operations mapped: 1=Seeding, 2=Transplanting, 3=Harvesting.
4. Each operation creates a Job Card, Stock Entry (Material Transfer for Manufacture), and records additional costs.
5. `submit_work_order_finish_goods()` completes the manufacturing cycle with a Manufacture stock entry.
6. Operation 3 is deferred to scheduler (`run_pending_harvesting_transfer`) to ensure Operation 2 completes first.

### UOM Conversion
1. FOMS Integration Settings stores UOM conversion table and item conversion table.
2. `get_uom()` maps FOMS UOM strings (kg, g, unit, packet) to ERPNext UOM names.
3. Item overrides (`get_item_overide()`) allow substituting one item for another during sync.
4. UOM overrides (`get_uom_overide()`) handle per-item UOM conversion differences.
5. On settings save, `update_uom_reference()` propagates conversion factors to Item UOM tables.

## Dependencies
- FOMS Integration Settings (URL, credentials, farm_id, sync toggles)
- Sync Log (frappe core - queues sync operations)
- FOMS Data Mapping (tracks raw data from FOMS and mapping status)
- Manufacturing Settings (default warehouses, auto-submit toggles)
- Company (cost centers, expense accounts)
- Rate Card (workstation and cost mappings per item)
- Packaging doctype (package definitions synced from FOMS)

## Notes
- `is_allowed_foms_company()` ensures sync only runs for the designated production company, preventing test/dev data from syncing.
- FOMS IDs are stored as fields on Items (`foms_raw_id`, `foms_product_id`), Batches (`foms_id`), Warehouses (`foms_id`), Customers/Suppliers (`foms_id`).
- The `no_copy` flag is set on FOMS ID fields to prevent duplication when copying documents.
- `OPERATION_MAP` and `OPERATION_MAP_NAME` constants define the mapping between operation numbers and names.
- `UOM_KG_CONVERTION` handles weight unit conversions (g->kg, mg->kg, etc.).
- Work order scrap handling: if percentage < 100, scrap materials entry is created for the remainder.
- Production variance journal entries are auto-created on Manufacture stock entry submission.
- The `pull_foms_data()` function provides a full reset+resync capability (clears all FOMS IDs and re-pulls).
- `dont_sync_foms_site` in site_config prevents accidental sync from development/staging environments.
