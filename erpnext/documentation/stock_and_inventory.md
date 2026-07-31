# Stock & Inventory

## Summary
Customizations to the stock ledger, item management, inventory accounting, and FOMS data mapping. Key additions include item department hierarchy, material number assignment from material groups, per-item stock account mapping via Part Number Settings, custom negative stock validation by batch, non-stock item handling, item packaging/UOM sync, stock transfer functions, salvage return, and integration with FOMS for item creation and batch tracking.

## Commits

### Item Structure & Department (2022-2023)
| Hash | Message | Date |
|------|---------|------|
| dda2525a2c | stockaging | 2022-10-20 |
| 8b603f20e4 | Item Category | 2023-02-20 |
| 58ec0c8ad6 | Item Department flow | 2023-02-06 |
| ac096920cd | itemnamelink | 2023-04-28 |
| 14ded8abf7 | add field non stock for others | 2023-10-10 |
| 0dcfa90488 | not include for non-stock | 2023-10-13 |

### FOMS Item Mapping & Creation (2024 Q1-Q2)
| Hash | Message | Date |
|------|---------|------|
| 7501f77d49 | create item | 2024-01-29 |
| 36448ec9df | mapping existing item | 2024-01-29 |
| abec16d051 | plot all item | 2024-05-06 |
| fc332a01cf | get raw mat on specific item | 2024-06-25 |
| c46ce06b9f | create direct manufacture finish item | 2024-07-02 |

### Stock Account Per Item (2024 Q3)
| Hash | Message | Date |
|------|---------|------|
| 675775ffc3 | add stock account based on item | 2024-09-25 |
| 801ede8dd5 | account stock for item purchase receipt | 2024-09-25 |
| 14f04a0069 | add stock account based on item | 2024-09-27 |
| 8a8ae938c9 | forbidding without inventory account | 2024-09-30 |
| 4d7abb6e37 | control item conversion | 2024-09-12 |
| 09fe8dfbdc | add item conversion | 2024-09-10 |

### Stock Validation & Reconciliation (2024 Q3-Q4)
| Hash | Message | Date |
|------|---------|------|
| 30a7598dce | validate balance stock | 2024-09-25 |
| 161c33a0a7 | create stock recon | 2024-10-31 |
| 9758e0ceac | only raw material with stock yes | 2024-11-14 |

### Stock Ledger & GL Alignment (2025)
| Hash | Message | Date |
|------|---------|------|
| b927c6b07e | update stock ledger and general ledger | 2025-03-19 |
| fa503e3db8 | validate negative stock new style | 2025-05-16 |
| 9fa7cea448 | disable stock partially | 2025-07-25 |
| 08c897a78a | realign Stock Ledger value with GL Value on scrap material | 2025-12-02 |
| 0201e35f54 | update stock level and reorder | 2025-12-12 |

### Item Enhancements (2025-2026)
| Hash | Message | Date |
|------|---------|------|
| 3f1c6a653e | change set item name based on item title | 2025-07-23 |
| 995b89011b | disable item pic update | 2025-10-24 |
| db42d766e7 | add item source price | 2025-12-18 |
| 525f3a0c4e | create salvage return and stock return | 2026-02-09 |
| b87815edeb | create stock transfer function | 2026-02-06 |
| 3745077362 | allow update after create item | 2026-05-11 |
| d0ec8750bc | set is free item if rate = 0 | 2026-07-03 |

... and 56 more commits

## Affected Files

**Item Core:**
- erpnext/stock/doctype/item/item.py
- erpnext/stock/doctype/item/item.json
- erpnext/stock/doctype/item/item_dashboard.py
- erpnext/stock/doctype/item/item_list.js
- erpnext/stock/doctype/item_department/item_department.py
- erpnext/stock/doctype/item_department/item_department.json
- erpnext/stock/doctype/item_price/item_price.json

**Stock Ledger & Accounting:**
- erpnext/stock/stock_ledger.py
- erpnext/stock/__init__.py
- erpnext/stock/utils.py
- erpnext/stock/reorder_item.py
- erpnext/controllers/stock_controller.py

**Stock Entries & Transactions:**
- erpnext/stock/doctype/stock_entry/stock_entry.py
- erpnext/stock/doctype/stock_entry/stock_entry.json
- erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.js
- erpnext/stock/doctype/purchase_receipt/purchase_receipt.py
- erpnext/stock/doctype/delivery_note/delivery_note.py

**Part Number Settings & Account Mapping:**
- erpnext/accounts/doctype/part_number_settings/part_number_settings.py
- erpnext/accounts/doctype/part_number_details/part_number_details.json

**FOMS Integration:**
- erpnext/foms/doctype/foms_data_mapping/foms_data_mapping.py
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py
- erpnext/foms/doctype/uom_foms_overide_item/uom_foms_overide_item.json
- erpnext/stock/page/batch_foms_details/batch_foms_details.js

**Reports:**
- erpnext/stock/report/stock_ageing/stock_ageing.py
- erpnext/stock/report/stock_balance/stock_balance.py
- erpnext/accounts/report/general_ledger/general_ledger.py

## Flow/Logic

### Item Department Hierarchy
1. On item validate, `insert_department()` auto-assigns root department if `item_department` child table is empty
2. Item Department is a child table doctype linking items to organizational departments
3. Used in item search queries to filter items by department (see Search & Filters feature)

### Material Number Assignment
1. `set_material_number()` is called during item validate
2. If `material_group` is set on the item, generates a sequential number from Material Group settings
3. Material Group doctype stores `number_start` and `number_end` range
4. `parse_material_group_series()` constructs a naming series pattern from the range (e.g., `10.####`)
5. `MATERIAL_MAP` constant maps item groups to series patterns (Seeds → 10.####, Nutrition → 11.####, etc.)
6. `get_item_material_group()` determines group from item_code prefix (RM-SD → Seeds, PR-LV → Vegetables (Lettuce), etc.)

### Per-Item Stock Account Mapping (Part Number Settings)
1. `get_warehouse_account_map()` in `erpnext/stock/__init__.py` is the central function for GL account resolution
2. After loading standard warehouse→account mappings, calls `get_part_number_account_settings(company)`
3. Part Number Settings stores item-level account overrides: maps item code/part number to specific GL accounts
4. `get_item_account()` resolves account priority: item-specific → part-number-specific → warehouse default → company default
5. WIP accounts support operation-specific mapping via Company's `operation_wip_account` child table

### Negative Stock Validation (Custom)
1. In `make_sl_entries()` in `stock_ledger.py`, custom batch-level negative stock check runs before creating SLEs
2. For each batch+warehouse combination, checks if outgoing qty exceeds available qty
3. Uses `get_previous_sle()` to get current `qty_after_transaction` for the batch
4. Throws `NegativeStockError` with detailed message showing shortfall amount, batch, warehouse, and voucher

### Non-Stock Item Handling
1. `force_to_non_stock()` on item validate: if Stock Settings has `force_to_non_stock_item` enabled, sets `is_stock_item = 0`
2. Work Orders skip non-stock items in required_items via `validate_non_stock_items()`
3. Child company items filter out "Raw Material" item group in queries

### Item Packaging & UOM Sync
1. `validate_package()` sets `is_package_item` flag based on packaging child table
2. `sync_uom_from_package()` synchronizes UOM Conversion Detail rows from packaging entries
3. Each packaging row creates/updates a UOM conversion with `is_packaging = 1`
4. Enforces single default packaging row; auto-sets first row as default if none specified

### Stock Transfer & Salvage Return
1. Custom stock transfer function creates Stock Entry with purpose "Material Transfer"
2. Salvage return creates return entries for damaged/salvaged goods
3. Moving stock restricted to Consignment Order context (`make moving stock only on CO`)

### UOM Global Description Sync
1. `update_uom_global_description()` on item validate syncs UOM descriptions bidirectionally
2. If user modifies `global_description` on item's UOM row, updates the master UOM doctype
3. If user didn't modify but master changed, pulls latest from master UOM

## Dependencies
- Part Number Settings (company-level doctype for item→account mapping)
- Material Group (doctype storing number series ranges)
- FOMS Integration (external system data mapping for items and batches)
- Manufacturing Settings (WIP warehouse for account mapping)
- Stock Settings (force_to_non_stock_item, sample_retention_warehouse)
- Company (operation_wip_account child table)

## Notes
- `get_warehouse_account_map()` caches results in `frappe.flags` for performance; includes account_currency_cache optimization
- FOMS items (with `foms_raw_id` or `foms_product_id`) cannot be deleted, only disabled
- Debit note item is singleton: only one item can have `debit_note_item = 1`
- Item description auto-syncs with item_name if unchanged from previous save
- Stock ageing report and stock balance report have GP-specific customizations
- Reorder level notifications sent only on new item creation (`send reorder level on new item only`)
- Free items auto-detected when rate = 0
