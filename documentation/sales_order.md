# Sales Order

## Summary
Sales Order customizations including FOMS integration for syncing orders, packaging/UOM queries, custom fields (sales_order_no, replacement qty, salad product), workflow state management, delivery date editability, qty conversion fixes, and batch number handling.

## Commits
| Hash | Message | Date |
|------|---------|------|
| dc2dfdfc4b | fix qty conversion sales order | 2026-05-22 |
| cddb43193e | fix rate from sales order | 2025-12-09 |
| 7ed0e95958 | add sales order create replacement qty | 2025-08-01 |
| 8eef1bc870 | sync sales order with salad | 2025-03-26 |
| 2e40f18555 | add salad product to Sales Order | 2025-03-26 |
| 84e17fee9e | ad editable sales order deliv date | 2025-03-17 |
| 59d316d211 | no ammend copy to sales order | 2025-02-17 |
| c64eb79352 | add sales order no | 2025-02-11 |
| 73edadbbff | fix sales order bug | 2025-01-20 |
| 1412b1cf79 | update sales order state | 2024-08-13 |
| 4c1b6f7fa0 | update sales order | 2024-08-12 |
| e3fd82e540 | update sales order id result | 2024-07-19 |
| 9146267775 | sync sales order | 2024-07-19 |
| d6c61a05cc | sync sales order | 2024-07-18 |
| e218a9b567 | crate sales order | 2024-07-04 |
| bd176f7aa9 | fix sales order calculations | 2024-07-04 |
| 425da706de | create button sales order | 2024-07-04 |
| 6c155d2825 | fix: Maintain same rate between Quotation and Sales Order | 2022-11-10 |
| fc6389280c | fix: add Sales Order reference in Material Request Dashboard | 2022-10-29 |
| d742e6d56b | fix: Total Sales amount update in project via Sales Order | 2022-10-26 |
| ccc58f48e3 | fix: allow to create Sales Order from expired Quotation | 2022-10-19 |

## Affected Files
**Core Doctype:**
- erpnext/selling/doctype/sales_order/sales_order.js
- erpnext/selling/doctype/sales_order/sales_order.json
- erpnext/selling/doctype/sales_order/sales_order.py
- erpnext/selling/doctype/sales_order_item/sales_order_item.json

**Related Doctypes:**
- erpnext/selling/doctype/quotation/quotation.js
- erpnext/selling/doctype/quotation/quotation.py
- erpnext/stock/doctype/delivery_note/delivery_note.json
- erpnext/stock/doctype/delivery_note/delivery_note.py
- erpnext/stock/doctype/packaging/packaging.json
- erpnext/manufacturing/doctype/work_order/work_order.json
- erpnext/manufacturing/doctype/work_order/work_order.py

**Controllers:**
- erpnext/controllers/accounts_controller.py
- erpnext/controllers/erp_api.py
- erpnext/controllers/foms.py
- erpnext/controllers/selling_controller.py
- erpnext/public/js/controllers/taxes_and_totals.js
- erpnext/public/js/controllers/transaction.js
- erpnext/stock/get_item_details.py

**Other:**
- erpnext/buying/doctype/request/request.js
- erpnext/buying/doctype/request/request.py
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py
- erpnext/hooks.py
- erpnext/stock/doctype/material_request/material_request_dashboard.py

## Flow/Logic

### FOMS Sales Order Sync
1. Sales Order is created/synced from FOMS (Factory Operations Management System) via `erp_api.py` endpoints.
2. `create_sales_order` endpoint receives FOMS data (customer, items, qty, delivery date).
3. Items are resolved using `foms_product_id` to find matching ERPNext Item codes.
4. The Sales Order is created with custom field `sales_order_no` linking back to FOMS reference.
5. On submit/update/cancel, `doc_events` in hooks triggers `erpnext.controllers.foms.sync_log` to sync state back to FOMS.

### Packaging & UOM Queries
1. In `sales_order.js`, the `package` field on items uses a custom query `get_packaging_available` that filters packaging options by item.
2. The `uom` field query filters by `parent` (item_code) and `is_packaging` flag based on `non_package_item` checkbox on the SO.
3. When `non_package_item` is unchecked (default), only items with `is_package_item=1` and `is_stock_item=1` are shown.

### Qty Conversion
1. When items have packaging UOMs, conversion factors are applied to calculate `stock_qty` from `qty`.
2. Fix ensures that rate is maintained correctly when converting between Quotation and Sales Order UOMs.
3. `selling_controller.py` and `get_item_details.py` handle the conversion logic.

### Replacement Qty
1. Custom field `replacement_qty` added to Sales Order Item.
2. Allows tracking replacement quantities separately from original order qty.
3. Used in work order creation to account for production overages.

### Salad Product Integration
1. Salad products from FOMS are mapped to Sales Order items.
2. Special handling in `controllers/foms.py` for detecting salad items during stock entry submission.
3. `detect_salad_items` hook on Stock Entry submit checks and processes salad-specific logic.

### Delivery Date Editability
1. `delivery_date` on Sales Order Items made editable after submit (via `allow_on_submit` or permission level).
2. Allows logistics to update expected delivery dates without amending the order.

### Workflow State Management
1. `update_sales_order_state` manages custom workflow transitions.
2. States are synced with FOMS via the `sync_log` mechanism on `on_update_after_submit`.

### Batch Number Handling
1. `from erpnext.stock.doctype.batch.batch import get_batch_no` imported in sales_order.py.
2. `load_bom_items()` called during validate to pre-populate BOM information.

## Dependencies
- `erpnext.controllers.foms` (FOMS sync, product resolution, packaging)
- `erpnext.controllers.erp_api` (API endpoints for FOMS)
- `erpnext.controllers.selling_controller.SellingController` (parent class)
- `erpnext.stock.get_item_details` (item pricing, UOM conversion)
- `erpnext.stock.doctype.batch.batch` (batch number resolution)
- FOMS Integration Settings (auto_submit, item_conversion mappings)
- hooks.py doc_events for Sales Order (on_submit, on_update_after_submit, on_cancel)

## Notes
- `non_package_item` checkbox on Sales Order controls whether item queries filter for packaged items only.
- Amending a Sales Order does NOT copy certain fields (`no ammend copy`) to prevent stale data propagation.
- Rate fix ensures that when a Quotation is converted to Sales Order, the rate is preserved regardless of UOM differences.
- The `get_packaging_available` query method is defined in `sales_order.py` and returns packaging records filtered by item.
