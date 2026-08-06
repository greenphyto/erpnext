# Warehouse

## Summary
Warehouse barcode/rack system with structured naming (store-row-lane-level-position), default warehouse setup per company, WIP warehouse handling, FOMS integration sync, and customer-linked warehouses.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 77264ce177 | fix default warehouse | 2026-06-01 |
| 262f12f2c0 | set default warehouse | 2026-05-29 |
| ef5db1ebb6 | fix currency and warehouse | 2026-03-17 |
| ab73c98198 | default warehouse set | 2026-02-12 |
| d425f4597d | add warehouse consignment | 2026-02-05 |
| 66880becf5 | set default selling warehouse | 2025-11-04 |
| fd476a816d | skip validate partially stock when use WIP warehouse | 2025-05-16 |
| 0374014eb4 | fix warehouse for modified sle | 2024-12-16 |
| 529a13085a | add detection multiple warehouse | 2024-12-16 |
| 0e7f38d721 | fix multiple warehouse | 2024-12-16 |
| 7b94a9ea1c | skip sync which to WIP warehouse | 2024-12-16 |
| f8cc60396c | fix warehouse for WIP | 2024-12-03 |
| e40bac1a05 | fix warehouse creating fields | 2024-11-05 |
| ce29995185 | set expense account warehouse | 2024-10-21 |
| a2459fb9fa | add default warehouse | 2024-09-20 |
| a1258e9510 | fix creating warehouse | 2024-09-05 |
| 755fc39475 | get all warehouse issue | 2024-09-05 |
| c09e6ede0f | delete warehouse sync | 2024-08-30 |
| 42f038253a | warehouse sync | 2024-08-21 |
| 32d64299a8 | filter warehouse | 2024-07-25 |
| 0fc7a0ee5b | if use warehouse name series | 2024-07-24 |
| e04186ff0a | sync warehouse | 2024-06-28 |
| f027ebf8cc | sync all warehouse | 2024-06-27 |
| 694aedf85e | working with warehouse | 2024-06-27 |
| 939fc3c907 | add restricted warehouse item | 2024-06-06 |
| 828f8ee2e8 | create warehouse real time | 2024-04-01 |
| 65790aee80 | create warehouse | 2024-04-01 |
| d4d0b972ca | validate wip warehouse | 2023-10-24 |
| c294652dab | fix: set `WIP Warehouse` in Job Card | 2022-11-10 |
| f923183b64 | fix: don't set WIP Warehouse if is checked in WO | 2022-11-10 |
| 0b09c31cb0 | fix: Increase columns width in Warehouse wise Item Balance Age and Value | 2022-11-07 |

## Affected Files

### Core Warehouse
- erpnext/stock/doctype/warehouse/warehouse.json
- erpnext/stock/doctype/warehouse/warehouse.py

### Stock Integration
- erpnext/stock/__init__.py
- erpnext/stock/doctype/bin/bin.py
- erpnext/stock/stock_balance.py
- erpnext/stock/doctype/stock_entry/stock_entry.js
- erpnext/stock/doctype/stock_entry/stock_entry.py
- erpnext/stock/doctype/delivery_note/delivery_note.js
- erpnext/stock/doctype/delivery_note/delivery_note.py
- erpnext/stock/doctype/scrap_request/scrap_request.js
- erpnext/stock/doctype/scrap_request/scrap_request.py

### Controllers
- erpnext/controllers/erp_api.py
- erpnext/controllers/foms.py
- erpnext/controllers/selling_controller.py
- erpnext/controllers/stock_controller.py

### Manufacturing
- erpnext/manufacturing/doctype/work_order/work_order.py
- erpnext/manufacturing/doctype/job_card/job_card.py
- erpnext/manufacturing/doctype/manufacturing_settings/manufacturing_settings.json

### Company & Boot
- erpnext/setup/doctype/company/company.json
- erpnext/startup/boot.py

### Consignment
- erpnext/gp_erp/doctype/consignment_request/consignment_request.js
- erpnext/gp_erp/doctype/consignment_request/consignment_request.json
- erpnext/gp_erp/doctype/consignment_request/consignment_request.py

### FOMS Integration
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py

## Flow/Logic

### 1. Warehouse Autoname with Rack/Barcode System
- If any of `row_no`, `lane_no`, `level_no` are set, the warehouse uses structured naming.
- Required fields: row_no, lane_no, level_no, colour, store, position.
- Name format: `{store}-{row_no}{lane_no}{level_no}{position}` (e.g., "MAIN-A1B2C").
- If rack fields are empty, validates all required fields and throws an error listing missing ones.
- Fallback: uses `warehouse_name + " - " + company_abbr` (standard ERPNext pattern).

### 2. Warehouse JSON Fields
- `foms_id`: External FOMS system warehouse ID for sync.
- `foms_name`: External FOMS system warehouse name.
- `is_wip_warehouse`: Flag marking Work-in-Progress warehouses.
- `warehouse_type`: Classification of warehouse.
- `only_for_item`: Restricts warehouse to specific items.
- `store`, `position`, `colour`, `row_no`, `lane_no`, `level_no`: Rack location fields.
- `customer`: Links warehouse to a specific customer (for consignment warehouses).

### 3. WIP Warehouse Handling
- WIP (Work-in-Progress) warehouses are marked with `is_wip_warehouse` flag.
- `get_wip_warehouse()` (in `controllers/foms.py`) retrieves all WIP warehouses.
- Stock entries skip partial issue validation for WIP warehouses.
- FOMS sync skips WIP warehouses to avoid syncing internal production locations.
- Manufacturing Work Orders use WIP warehouse for in-process materials.

### 4. Default Warehouse Setup
- Company doctype stores default warehouse settings.
- Default selling warehouse is set per company for sales transactions.
- `startup/boot.py` loads default warehouse info at application boot.
- Controllers (`selling_controller.py`, `stock_controller.py`) auto-set default warehouses on transactions.

### 5. Warehouse Account Mapping
- `account` field links warehouse to a GL account for perpetual inventory.
- `warn_about_multiple_warehouse_account()`: On account change, warns if stock value was previously booked to different accounts.
- `set expense account warehouse`: Ensures proper expense account assignment.

### 6. FOMS Warehouse Sync
- Warehouses are synced with the external FOMS system via `foms_integration_settings.py`.
- `foms_id` and `foms_name` track the external system reference.
- Sync can create warehouses in real-time or bulk sync all.
- WIP warehouses are excluded from sync.

### 7. Consignment Warehouse
- Warehouses can be linked to a customer via the `customer` field.
- Used for consignment stock management where goods are stored at customer locations.
- Consignment Request uses these customer-linked warehouses.

### 8. Warehouse Deletion Safety
- Checks for existing stock (actual_qty, reserved_qty, ordered_qty, etc.) before deletion.
- Checks for Stock Ledger Entries.
- Checks for child warehouses.
- Cleans up Bin records on deletion.

## Dependencies
- Company doctype (company abbr for naming, default warehouse settings)
- Stock Ledger Entry (deletion validation)
- Bin doctype (projected qty, stock levels)
- FOMS Integration Settings (external sync)
- Work Order / Job Card (WIP warehouse usage)
- Consignment Request (customer-linked warehouses)
- Manufacturing Settings (WIP warehouse configuration)

## Notes
- The rack naming system (`store-row_no+lane_no+level_no+position`) creates barcode-scannable warehouse locations.
- All rack fields (row_no, lane_no, level_no, colour, store, position) must be set together - partial rack data throws an error.
- WIP warehouses are treated specially throughout the system: skipped in FOMS sync, exempted from partial issue validation, and used as intermediate locations in manufacturing.
- The `only_for_item` field allows restricting a warehouse to store only specific items.
- Multiple warehouse account warnings help prevent accounting inconsistencies in perpetual inventory.
