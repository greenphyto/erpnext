# Manufacturing

## Summary
Comprehensive customizations to Work Order, BOM, Workstation, and Job Card modules. Key additions include custom naming series for BOM/Work Order, per-KG/per-Qty cost calculation on workstations, operation-based WIP accounting, packet size management, tolerance qty for overproduction, cost editing controls, salad recipe handling, and FOMS lot-based work order naming.

## Commits

### Initial Setup & Naming (2022-2023)
| Hash | Message | Date |
|------|---------|------|
| 8323775282 | feat: Workstation Type for BOM | 2022-11-08 |
| 3f79a057e4 | fix: make BOM required in SCR Item | 2022-11-05 |
| ed2a093e49 | fix: BOM cost update message | 2022-10-20 |
| 735e393866 | add work order series and bom series | 2023-10-19 |
| e57c529661 | fix series bom | 2023-10-23 |
| fa4f4deecc | set autoname work order | 2023-10-25 |
| 6e8de2d937 | add revision bom name | 2023-12-29 |

### BOM & Work Order Creation from FOMS (2024 Q1-Q2)
| Hash | Message | Date |
|------|---------|------|
| 91bedcad89 | create bom product | 2024-01-30 |
| b3f0371e57 | make bom and operation | 2024-01-30 |
| adbb6efe4d | find existing bom | 2024-01-30 |
| ae5b0e0b22 | create work order | 2024-02-15 |
| 89b5d6cda0 | create and submit work order | 2024-02-21 |
| 8ccd7cfd84 | create bom version 2 | 2024-03-15 |
| 5de57fa310 | fix create work order | 2024-03-18 |
| 3f23b72f69 | work order transfer material | 2024-03-25 |
| ff0f841d47 | calculation per kg BOM and routing | 2024-06-19 |

### Cost & Rate Enhancements (2024 Q3-Q4)
| Hash | Message | Date |
|------|---------|------|
| 49e0d663d4 | calculate cost on work order | 2024-08-13 |
| 955b083473 | adjust costing at BOM | 2024-08-13 |
| 44424b3d82 | add BOM rate log | 2024-11-01 |
| 4e749a6233 | update BOM rate by GRN | 2024-11-04 |
| f7a71e0bdb | set rate based on BOM | 2024-11-06 |
| 0c53864750 | allow single complete work order | 2024-11-07 |

### Production Controls & Fixes (2025)
| Hash | Message | Date |
|------|---------|------|
| c1b1a9829d | get packet size default and rate based on BOM | 2025-07-29 |
| 3806e08aaf | make WO rate like BOM rate | 2025-07-29 |
| 0e919f1cd4 | mf: add cos production variance | 2025-06-02 |
| cc1e60dbcc | add settings for marketing and production | 2025-10-30 |
| 380b1fe546 | prod: fixing work order different notification | 2025-11-21 |
| 748c8b4ef7 | prod: fix manufacturing rate | 2025-12-04 |

### Recent Updates (2026)
| Hash | Message | Date |
|------|---------|------|
| 677f51b638 | add lead time days to BOM | 2026-02-03 |
| b045217793 | add tolerance qty for work order | 2026-04-15 |
| a7305d7039 | dont copy rate from BOM | 2026-04-30 |
| 14bded6ccb | missing work order rate notification | 2026-04-30 |

... and 55 more commits

## Affected Files

**Work Order:**
- erpnext/manufacturing/doctype/work_order/work_order.py
- erpnext/manufacturing/doctype/work_order/work_order.js
- erpnext/manufacturing/doctype/work_order/work_order.json
- erpnext/manufacturing/doctype/work_order_item/work_order_item.json
- erpnext/manufacturing/doctype/work_order_operation/work_order_operation.json

**BOM:**
- erpnext/manufacturing/doctype/bom/bom.py
- erpnext/manufacturing/doctype/bom/bom.js
- erpnext/manufacturing/doctype/bom/bom.json
- erpnext/manufacturing/doctype/bom_operation/bom_operation.json

**Workstation:**
- erpnext/manufacturing/doctype/workstation/workstation.py
- erpnext/manufacturing/doctype/workstation/workstation.json
- erpnext/manufacturing/doctype/workstation_type/workstation_type.py
- erpnext/manufacturing/doctype/workstation_type/workstation_type.js

**Job Card & Settings:**
- erpnext/manufacturing/doctype/job_card/job_card.py
- erpnext/manufacturing/doctype/job_card/job_card.json
- erpnext/manufacturing/doctype/manufacturing_settings/manufacturing_settings.json
- erpnext/manufacturing/doctype/routing/routing.py

**BOM Rate Log (Custom Doctype):**
- erpnext/stock/doctype/bom_rate_log/bom_rate_log.py
- erpnext/stock/doctype/bom_rate_log/bom_rate_log.json

**Notifications:**
- erpnext/gp_erp/notification/missing_work_order_rate/

**Stock & Controllers:**
- erpnext/stock/doctype/stock_entry/stock_entry.py
- erpnext/controllers/erp.py
- erpnext/controllers/foms.py
- erpnext/stock/stock_ledger.py

## Flow/Logic

### BOM Naming (autoname)
1. BOM name follows pattern: `BOM-{item_code}-{operation_no}{version_index}`
2. System finds existing BOMs matching pattern, extracts max version index, increments by 1
3. Version index is zero-padded to 3 digits (e.g., `001`)
4. If name > 136 chars, item name is truncated to fit

### BOM Costing
1. `calculate_cost()` computes raw material cost + operating cost
2. Raw material rate sourced from Valuation Rate, Last Purchase Rate, or Price List (configurable via `rm_cost_as_per`)
3. `get_workstation_cost()` fetches rates from Workstation based on `calculation_type`:
   - "Per KG" / "Per Qty": uses `per_qty_rate_electricity`, `per_qty_rate_consumable`, `per_qty_rate_machinery`, `per_qty_rate_wages`
   - "Per Hour" (default): uses `hour_rate_electricity`, `hour_rate_consumable`, `hour_rate_labour`, `hour_rate_rent`
4. Salad recipe BOMs force `rm_cost_as_per = "Last Purchase Rate"` and set `do_not_explode` on all items

### Work Order Naming (autoname)
1. If `operation_no` is set, appends alpha suffix (A/B/C/D/E/F) to series
2. If `foms_lot_name` exists, uses it as base; otherwise uses `naming_series`
3. Pattern: `{base}-.###.-{alpha}` or `{base}-.###`

### Work Order Validation & Execution
1. `validate()` calls: validate_production_item, validate_sales_order, set_default_warehouse, get_workstation_cost, calculate_operating_cost, validate_qty, set_packet_size, set_required_items, validate_non_stock_items, set_is_salad_item
2. `validate_non_stock_items()` removes non-stock items from required_items list
3. `calculate_operating_cost()` uses `gross_weight` for Per KG/Qty calculations instead of qty
4. `get_status()` determines status from Stock Entries:
   - Checks manufacture entries and return entries
   - If return qty >= WO qty → Closed
   - If manufactured qty >= qty (or any completion with `allow_single_completed_work_order`) → Completed
   - Otherwise → In Process or Not Started

### Work Order Cost Editing Control
1. `validate_cost_editing()` on update_after_submit checks cost fields (electrical, consumable, machinery, wages, rent)
2. If any cost field changed AND `completed_qty != 0`, throws error preventing edits to completed operations
3. `write_opr_version()` sets version to "Custom" if cost editing enabled, otherwise fetches version from Workstation

### Workstation Naming
1. If `item_code` is set, name = `Farm-{item_code}-{operation}-{version_index}`
2. Otherwise, name = `{workstation_name}-{version_index}`
3. Version index uses same 3-digit zero-padded logic as BOM
4. Validates no duplicate workstation exists for same item+operation combination

### Workstation Calculation Types
1. "Per KG": only valid for items with stock_uom = "Kg"
2. "Per Qty": general per-unit costing
3. "Per Hour" (default): time-based costing
4. When type is Per Qty/Per KG, hour rates are zeroed out and vice versa

### Tolerance Qty / Overproduction
1. `overproduction_percentage_for_work_order` in Manufacturing Settings controls allowed overproduction
2. `allow_single_completed_work_order` allows marking WO as Completed after any single manufacture entry

### Sales Order Integration
1. On submit, `update_sales_order(state="Start")` links WO to SO and updates work_order_reference
2. On completion, `update_sales_order(state="Finish")` updates work progress on SO

## Dependencies
- FOMS Integration (foms_lot_name, FOMS Data Mapping for creating BOMs/WOs)
- Stock Entry (manufacture purpose, material transfer)
- Sales Order (production tracking)
- Part Number Settings (stock account mapping)
- Manufacturing Settings (overproduction %, WIP warehouse, default warehouses)
- BOM Rate Log (tracks rate changes from GRN)

## Notes
- Non-stock items are automatically removed from Work Order required_items
- Salad products have special BOM handling: forces Last Purchase Rate, disables explosion, sets 14-day storage duration
- `allow_single_completed_work_order` is a GP-specific setting allowing WO completion after any manufacture qty
- WIP accounting supports operation-specific accounts via Company's `operation_wip_account` child table
- Cost editing is locked after operation completion to preserve historical accuracy
- Work Order status "Closed" is triggered by return qty meeting WO qty (different from standard ERPNext)
