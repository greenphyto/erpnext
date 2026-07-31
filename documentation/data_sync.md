# Data Sync

## Summary
Data synchronization between ERPNext and external systems including FOMS, MinIO backup, and UOB bank sync. Handles bidirectional sync of items, batches, stock levels, suppliers, customers, warehouses, and file logs. Uses a Sync Log mechanism with controller pattern to queue and process sync operations.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 5223cd0f30 | add sync manual button to item | 2026-05-11 |
| bc2ef7e428 | sync item material group and variant | 2026-05-08 |
| 63b041e082 | add lead time sync | 2026-02-04 |
| 1b3270dda8 | show button sync only for new version | 2025-12-01 |
| 3f9200ac49 | uob; fix failed syncing status | 2025-11-19 |
| 597b842d72 | ai: add manual sync button | 2025-11-06 |
| 321d4dbbd3 | sync item desc when rename | 2025-11-05 |
| 1a7e17a5bf | ai: save result from sync and fix syncing manual | 2025-10-23 |
| 414e18632c | ai: remove uob sync log | 2025-10-10 |
| 4d07bc790c | add sync button | 2025-09-15 |
| a4bb667086 | add sync now button | 2025-07-11 |
| ebe96f6df9 | delete doctype sync log | 2025-06-30 |
| 4018108afe | sync if new | 2025-06-24 |
| 4b20990a72 | sync PIC value | 2025-06-20 |
| b5f76b35be | move doctype Sync Log | 2025-05-07 |
| 3efc6f01e6 | ini UOB sync log | 2025-05-05 |
| 58b40da3c6 | fix sync missing products | 2025-04-03 |
| fb83df93f3 | switch to weight order on salad sync | 2025-03-25 |
| 0836f4f44f | skip sync if from repack and manufacture | 2025-03-24 |
| 54fff44b35 | sync sle with settings | 2024-12-17 |

## Affected Files
**Sync Controllers & Core Logic**
- erpnext/controllers/foms.py (main sync controller with sync_controller pattern)
- erpnext/controllers/erp_api.py (API endpoints for external system calls)
- erpnext/controllers/erp.py

**FOMS Integration Settings**
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.js
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.json

**FOMS Data Mapping**
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.py
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.js
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.json

**MinIO Backup**
- erpnext/foms/doctype/minio_backup_settings/minio_backup_settings.py
- erpnext/foms/doctype/minio_backup_settings/minio_backup_settings.js
- erpnext/foms/doctype/minio_backup_settings/minio_backup_settings.json

**UOB Sync Log**
- erpnext/foms/doctype/uob_sync_log/uob_sync_log.py
- erpnext/foms/doctype/uob_sync_log/uob_sync_log.js
- erpnext/foms/doctype/uob_sync_log/uob_sync_log.json
- erpnext/uob/doctype/uob_file_log/uob_file_log.py

**Item & Stock**
- erpnext/stock/doctype/item/item.py
- erpnext/stock/doctype/item/item.js
- erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.py
- erpnext/stock/doctype/batch/batch.json

**Sales & Buying**
- erpnext/selling/doctype/sales_order/sales_order.py
- erpnext/selling/doctype/customer/customer.py
- erpnext/buying/doctype/request/request.py

## Flow/Logic

### Sync Controller Pattern
1. Documents (Supplier, Customer, Sales Order, etc.) trigger a `create_log()` call on save/submit/delete, creating a "Sync Log" record with the document name and update type.
2. `sync_controller(doctype, callback)` fetches pending Sync Log entries for the given doctype.
3. For each log entry, it instantiates a `FomsAPI()` and calls the provided callback function (e.g., `_update_foms_supplier`).
4. The callback transforms ERPNext data into FOMS API format and calls the appropriate API method.
5. On success, `update_success()` marks the Sync Log as completed; on failure, `update_error()` stores the error.

### FOMS Data Pull (GET operations)
1. `GetData` class orchestrates pulling data from FOMS (raw materials, products, batches, work orders).
2. It calls the FOMS API to fetch all records, iterates through results, and calls a `post_process` callback.
3. Results are stored in `FOMS Data Mapping` doctype as raw JSON data with status tracking (Unknown -> In Progress -> Mapped).
4. Mapped records link to their corresponding ERPNext document (e.g., Item, BOM, Work Order).

### FOMS Data Push (POST operations)
1. On document events (save, submit, cancel), sync hooks create Sync Log entries.
2. Supported push operations: Supplier, Customer, Sales Order, Delivery Note, Request/Forecast, Scrap Request, Department, Stock Reconciliation, Warehouse.
3. Each push transforms ERPNext data to FOMS format and calls `FomsAPI.req()` which handles authentication, request, and response logging.
4. `is_allowed_foms_company()` gate ensures only the designated company syncs to FOMS.

### Stock Ledger Entry (SLE) Sync
1. `sync_sle()` is triggered on stock ledger entry creation.
2. Only processes positive qty entries with batch numbers.
3. Calculates total batch qty in warehouse and calls `update_foms_batch()`.
4. Skips WIP warehouses (from Manufacturing Settings and warehouses marked `is_wip_warehouse`).
5. Controlled by the `sync_sle` setting in FOMS Integration Settings.

### MinIO Backup
1. `MinIOBackupSettings` stores MinIO connection details (host, access_key, secret_key, bucket, folder).
2. `upload_backup()` is called (manually or via scheduler).
3. Takes a database backup using `frappe.utils.backups.new_backup()` with a configurable doctype list.
4. Uploads the compressed backup file to the configured MinIO bucket/folder using the MinIO Python client.

### UOB Sync
1. UOB (bank) sync log tracks file-based synchronization with UOB banking system.
2. Handles payment approval workflows and file log tracking.
3. Moved from `erpnext/foms/doctype/uob_sync_log/` to `erpnext/uob/doctype/uob_sync_log/` over time.

### Manual Sync
1. Items have a "Sync to FOMS" button (`create_new_foms_item` whitelisted function).
2. Creates the item's material group and variant type in FOMS if they don't exist.
3. Creates the raw material record in FOMS and syncs available batches.
4. Only allowed for specific material groups (Miscellaneous, Accessories, Seeds, Herbs, etc.).

## Dependencies
- FOMS Integration Settings (credentials, farm_id, sync toggles)
- Sync Log (frappe.core.doctype.sync_log)
- FOMS Data Mapping (tracks incoming data mapping status)
- Manufacturing Settings (WIP warehouse, default FG warehouse)
- MinIO Python client library (`minio`)
- Company settings (allowed FOMS company)

## Notes
- The `FomsAPI` class handles token-based authentication with automatic login on first request.
- `convert_data()` recursively replaces None values with empty strings before JSON serialization (FOMS API requirement).
- Sync is gated by `is_enable_integration()` which checks both the enable flag and a `dont_sync_foms_site` conf variable to prevent sync on certain environments.
- Operation 3 (Harvesting) finish goods are scheduled rather than processed immediately to allow preceding operations to complete.
- `run_pending_harvesting()` and `run_pending_harvesting_transfer()` are scheduler jobs that process queued work order operations.
- Stock tolerance (`STOCK_TOLERANCE`) is used during material transfer to handle minor qty differences.
- Item override and UOM override maps from FOMS Integration Settings allow mapping different items/UOMs between systems.
