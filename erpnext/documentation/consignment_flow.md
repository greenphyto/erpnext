# Consignment Order & Request Flow

## Summary
Custom doctypes for managing consignment stock between the company and customers. A **Consignment Request** represents a customer's request to hold stock on consignment. A **Consignment Order** is an internal stock transfer document that moves inventory from the company warehouse to a customer-specific consignment warehouse. The flow continues through stock returns, salvage processing, and eventual sales invoicing.

## Commits
| Hash | Message | Date |
|------|---------|------|
| d0970826c7 | fix CO bug on cancel | 2026-07-22 |
| cbd385d2f3 | fix consignment return | 2026-06-01 |
| 83463a6623 | fix consignment status | 2026-06-01 |
| 20df918f36 | fix consignment return | 2026-06-01 |
| 7f87a477c6 | fix consignment status | 2026-06-01 |
| 58bd67ed76 | fix series add consignment | 2026-05-31 |
| 621bc0ad9c | fix series add consignment | 2026-05-31 |
| 44e0914c01 | print format for consignment order | 2026-05-26 |
| 74911c70c5 | sales invoice and stock for consignment | 2026-05-25 |
| 2ca388f650 | map consignment order | 2026-05-25 |
| b89eebf92b | new doctype consignment order | 2026-05-25 |
| 12fb9a0515 | Merge branch 'consignment-flow' into gpprod.v14.3.1 | 2026-03-02 |
| d08da6fadf | add back button consignment | 2026-02-19 |
| 1c047c45f8 | fix multi-batch issues on consignment | 2026-02-10 |
| b0edbc8919 | update consignment from DN | 2026-02-10 |
| f4d70a7475 | add warehouse consignment | 2026-02-05 |
| 5e225ee20c | create consignment doctype | 2026-02-04 |

## Affected Files

**Consignment Request (doctype)**
- `erpnext/gp_erp/doctype/consignment_request/consignment_request.py`
- `erpnext/gp_erp/doctype/consignment_request/consignment_request.js`
- `erpnext/gp_erp/doctype/consignment_request/consignment_request.json`

**Consignment Order (doctype)**
- `erpnext/gp_erp/doctype/consignment_order/consignment_order.py`
- `erpnext/gp_erp/doctype/consignment_order/consignment_order.js`
- `erpnext/gp_erp/doctype/consignment_order/consignment_order.json`

## Flow/Logic

### 1. Consignment Request (CR) — Created First
1. User creates a Consignment Request for a customer, selecting items (filtered to `item_group = Products`, package items only by default).
2. Warehouses are configured:
   - `set_warehouse` — source warehouse (company default)
   - `con_warehouse` — customer's consignment warehouse (filtered by customer)
   - `salvage_warehouse` — where returned goods go for salvage
   - `repack_warehouse` — for repacking operations
3. On submit, a **customer-specific warehouse** is auto-created under a "Consignment Warehouse" parent group if one doesn't exist (linked via `warehouse.customer` field).
4. Credit limit is checked on submit.

### 2. Consignment Order (CO) — Stock Transfer to Customer
1. From a submitted CR, user clicks **Create > Consignment Order (Stock Transfer)**.
2. The `make_consignment_order` mapper creates a CO with:
   - `set_target_warehouse` = CR's `con_warehouse`
   - `set_warehouse` = CR's `set_warehouse`
   - Items mapped with `qty = requested_qty - already_transferred_qty`
   - Batch auto-selected via FIFO from source warehouse
3. CO extends `DeliveryNote` but overrides key behavior:
   - **No GL entries** — `get_gl_entries()` returns `[]`
   - **No Sales Order status updates** — `status_updater = []`
   - Stock Ledger creates entries for both source (debit) and target (credit) warehouses
4. On submit, CO calls `update_consignment_request_status()` which syncs `transfer_qty` back to the CR items.
5. Naming series: `CON-.YYYY.-.#####`

### 3. Stock Return (from consignment warehouse back to salvage)
1. From CR, user clicks **Create > Stock Return**.
2. Creates a Stock Entry (type: "Consignment Return") moving stock from `con_warehouse` → `salvage_warehouse`.
3. Qty defaults to `transfer_qty - returned_qty` (what's still at customer).
4. On submit, the `stock_entry_controller` hook updates CR items' `returned_qty` and recalculates `sold_qty = transfer_qty - returned_qty`.

### 4. Salvage Process (repack returned goods)
1. From CR, user clicks **Create > Salvage Process**.
2. Creates a Stock Entry (type: "Salvage Process (Repack)") that moves items from `salvage_warehouse` → `set_warehouse` (back to main stock).
3. Adds paired rows: one source row (from salvage) and one target row (to main warehouse) per batch.

### 5. Sales Invoice (billing the consigned goods sold)
1. From CR, user clicks **Create > Sales Invoice**.
2. Creates a Sales Invoice with `update_stock = 1`, warehouse set to `con_warehouse`.
3. Qty = `transfer_qty - returned_qty - billed_qty` (what was sold and not yet billed).
4. Batch selection uses FIFO filtered to batches that were actually transferred via Consignment Orders.
5. On submit, the `billing_consignment_controller` hook updates CR items' `billed_qty`.

### 6. Status Tracking on Consignment Request
The CR tracks progress via percentage fields calculated in `sync_qty()`:
| Field | Calculation |
|-------|-------------|
| `per_transfer` | `total_transfer_qty / total_qty * 100` |
| `per_return` | `total_return_qty / total_transfer_qty * 100` |
| `per_sold` | `total_sold_qty / total_transfer_qty * 100` |
| `per_billed` | `total_billed_qty / total_sold_qty * 100` |
| `per_delivered` | `total_delivered_qty / total_sold_qty * 100` |

**Status transitions:**
- `Waiting for Transfer` — nothing transferred yet
- `Partially Transferred` — some items transferred
- `Transferred to Customer` — 100% transferred
- `Returned and To Bill` — returns/sales exist but no delivery
- `To Bill` — delivered but not fully billed
- `Completed` — fully billed

## Dependencies

- **Delivery Note** — Consignment Order inherits from `DeliveryNote` (Python class and JS includes)
- **Stock Entry** — Used for Consignment Transfer, Consignment Return, and Salvage Process operations
- **Stock Entry Type** — Custom types: "Consignment Transfer", "Consignment Return", "Salvage Process (Repack)"
- **Sales Invoice** — Final billing document created from CR
- **Warehouse** — Auto-creates customer-linked warehouses under "Consignment Warehouse" group
- **Batch** — FIFO batch selection used throughout for traceability
- **SellingController** — CR inherits from `SellingController` for pricing/tax handling

## Notes

- **No accounting entries on CO**: The Consignment Order deliberately returns empty GL entries. This prevents "Cost Center is mandatory" errors during Repost Item Valuation.
- **Warehouse field is cleared on CO items**: The `warehouse` (source for DN) is intentionally blanked; only `target_warehouse` is used. The JS hides the warehouse column and shows target_warehouse instead.
- **Cancel behavior**: On CO cancel, `ignore_linked_doctypes` includes GL Entry, Stock Ledger Entry, and Repost Item Valuation to allow clean cancellation.
- **Script load guard**: The JS uses `window.__consignment_order_script_loaded` to prevent double-initialization since it includes the full Delivery Note script.
- **Item filter**: CR defaults to package items only (`is_package_item=1, is_stock_item=1`) unless `non_package_item` is checked.
- **Hook controllers**: `stock_entry_controller` and `billing_consignment_controller` are meant to be called from hooks on Stock Entry and Sales Invoice/Delivery Note submit/cancel events to keep CR quantities in sync.
- **sold_qty derivation**: `sold_qty = transfer_qty - returned_qty` — it represents what remains at the customer (presumed sold).
