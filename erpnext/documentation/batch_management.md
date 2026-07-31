# Batch Management

## Summary
Custom batch status tracking, validation, and lifecycle management. Includes batch status field (Active/Empty/Expired), FOMS batch integration and syncing, batch availability strategies (FIFO, Expired First, Small First), expiry handling with company-specific shelf life, LOT ID search, and batch picking for multi-batch fulfillment.

## Commits
| Hash | Message | Date |
|------|---------|------|
| d81fc9c722 | add patches for batch | 2026-07-23 |
| 4972276d96 | add batch status field | 2026-07-23 |
| 7bbab0b4ea | skip validate batch when cancel return | 2026-07-06 |
| 52b820ced4 | fix multiple batch invoice | 2026-06-23 |
| 667b34319a | update batch permissions | 2026-05-12 |
| 5c4266a9f2 | sync batch after insert | 2026-05-11 |
| 35b90c4f43 | fix sync multiple batch GRN | 2026-03-16 |
| d7b8d1ae89 | add settings for copy batch for internal transaction | 2026-02-06 |
| ccfeceab90 | search batch with LOT ID | 2026-01-20 |
| 92025d37d7 | allow replacement to use expiry batch | 2026-01-29 |
| 7c65c8d6e8 | allow use expired batch on donation and marketing | 2026-01-21 |
| 1368b2c0ae | copy batch no to sub company | 2026-01-22 |
| ae3fa61ada | foms: set rate based on batch and warehouse | 2025-12-05 |
| b667dd8b38 | prod: make batch qty editable and uom | 2025-11-04 |
| 6ff26f110d | prod: get batch mapping | 2025-11-04 |
| 06f3216efa | update stock recon with update batch recon | 2025-02-28 |
| 110b5449d1 | init report batch delivery | 2025-02-12 |
| 38c2f1d0d0 | move stock batch validation | 2025-01-22 |
| 686edc2c52 | ini batch bundle report details | 2024-10-16 |
| 9446bd36fb | get batch from foms | 2024-07-23 |

... and 42 more commits

## Affected Files

**Core Batch Logic**
- erpnext/stock/doctype/batch/batch.py
- erpnext/stock/doctype/batch/batch.json

**FOMS Integration**
- erpnext/controllers/foms.py
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.json
- erpnext/stock/page/batch_foms_details/batch_foms_details.js
- erpnext/stock/page/batch_foms_details/batch_foms_details.css
- erpnext/stock/page/batch_foms_details/batch_foms_details.json
- erpnext/stock/dashboard/batch_foms.html
- erpnext/stock/dashboard/batch_foms_list.html

**Stock Operations**
- erpnext/stock/doctype/stock_entry/stock_entry.py
- erpnext/stock/doctype/stock_entry/stock_entry.json
- erpnext/stock/doctype/delivery_note/delivery_note.py
- erpnext/stock/doctype/delivery_note/delivery_note.js
- erpnext/stock/doctype/purchase_receipt/purchase_receipt.py
- erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.py
- erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.js
- erpnext/stock/doctype/stock_ledger_entry/stock_ledger_entry.py
- erpnext/stock/stock_ledger.py

**Transaction Controllers**
- erpnext/controllers/accounts_controller.py
- erpnext/controllers/stock_controller.py
- erpnext/controllers/erp_api.py
- erpnext/controllers/queries.py
- erpnext/public/js/controllers/transaction.js
- erpnext/public/js/utils/serial_no_batch_selector.js

**Reports**
- erpnext/foms/report/batch_delivery/batch_delivery.py
- erpnext/foms/report/batch_delivery/batch_delivery.js

**Invoices & Sales**
- erpnext/accounts/doctype/sales_invoice/sales_invoice.py
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.py
- erpnext/selling/doctype/sales_order/sales_order.py

**Patches**
- erpnext/patches/gp/set_batch_status.py
- erpnext/patches.txt

## Flow/Logic

### 1. Batch Status Lifecycle
The `get_batch_status()` function in `batch.py` determines batch status:
- **Empty**: `batch_qty <= 0`
- **Expired**: `expiry_date` is in the past
- **Active**: has stock and not expired

Status is set automatically on `validate()` via `set_status()`. A patch (`set_batch_status.py`) retroactively sets status on existing batches.

### 2. Batch Creation & Naming
- `autoname()`: Uses `batch_id` if provided, otherwise generates from item's `batch_number_series`, stock settings naming series, or random hash.
- `flags.add_last_symbol`: Appends a suffix (e.g., `-1`) for related batches.

### 3. Shelf Life & Expiry Date
- `get_item_shelf_life_in_days()`: Resolves shelf life from Item defaults, but prefers company-specific mapping from the `Shell Life Companies` child table.
- `before_save()`: Auto-calculates `expiry_date` from `manufacturing_date + shelf_life_in_days`.
- Throws error if item has expiry tracking enabled but no shelf life configured.

### 4. Batch Availability Strategies
`get_available_batch_portion()` supports multiple picking strategies:
- **FIFO** (default): Sort by creation date
- **Expired First**: Sort by expiry date ascending (use nearest-expiry first)
- **Small First**: Sort by quantity ascending (deplete small batches first)

The function picks batches to fulfill a required qty, splitting across multiple batches if needed. It excludes WIP warehouses and expired batches.

### 5. Batch Picking (`pick_batches`)
Whitelisted API that:
1. Converts required qty to stock UOM using conversion factor
2. Iterates batches (FEFO order from `get_batches()`)
3. Returns list of batch allocations with both stock UOM and requested UOM quantities

### 6. FOMS Batch Integration (Page: batch_foms_details)
A dedicated page for syncing batch data between FOMS (external system) and ERPNext:
- **Fetch Data**: Calls FOMS API to retrieve current batch quantities
- **Update FOMS Batch**: Syncs ERP batch qty to FOMS
- **Update ERP Batch**: Syncs FOMS batch qty to ERP via Stock Reconciliation
- Displays comparison table: FOMS qty vs ERP qty, with expiry dates
- Supports filtering by batch number, hiding expired/empty batches
- Creates draft Stock Reconciliation documents for bulk updates

### 7. Batch Validation Rules
- Skip batch validation when canceling returns (`skip validate batch when cancel return`)
- Allow expired batches for donation and marketing transactions
- Allow replacement orders to use expired batches
- Copy batch numbers to sub-company for internal transactions
- LOT ID search capability in batch selector

### 8. Stock Operations
- `set_batch_nos()`: Auto-assigns batch numbers for outgoing items using FEFO
- Validates batch qty is sufficient on submit
- `get_available_batch()`: Returns batches with sufficient qty excluding WIP warehouses

## Dependencies
- FOMS Integration Settings (external API configuration)
- Stock Reconciliation (for batch qty adjustments)
- Manufacturing Settings (WIP warehouse exclusion)
- Stock Ledger Entry (batch qty calculation)
- Batch-Wise Balance History report (used by availability functions)

## Notes
- Batch status is a computed field - it recalculates on every validate, not stored permanently until the patch sets it.
- `get_available_batch_portion()` loads full batch documents (`frappe.get_doc`) for each batch to check expiry - may be slow with many batches.
- WIP warehouses are excluded from availability checks both by the `is_wip_warehouse` flag and the Manufacturing Settings default.
- The FOMS batch page creates Stock Reconciliation in draft - user must manually submit after reviewing all changes.
- Company-specific shelf life uses `Shell Life Companies` child table (note: typo "Shell" instead of "Shelf" in the doctype name).
