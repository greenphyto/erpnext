# Packaging & Weight

## Summary
Comprehensive packaging management system: package size configuration, carton UOM handling, customer-specific packaging preferences, unit weight tracking, total KG calculation, FOMS packaging sync, and packaging material integration with BOMs and work orders.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 778fe4ec21 | fix: add unit_weight to _add_item_to_request so total_weight calculates correctly | 2026-07-10 |
| d543ad45ce | fix: packaging display '200 Gr' in preview, full title in Request doc UOM | 2026-07-10 |
| 25701ed38a | fix: uom field now uses packaging title instead of UOM name | 2026-07-10 |
| 9a62967331 | fix: restore uom field for Request Items, move Total KG after Packaging | 2026-07-10 |
| 71fd4c6161 | fix: button position, silent skip empty rows, Packaging column with Total KG | 2026-07-10 |
| 0fd63ccb9d | add package size | 2026-07-02 |
| 6cf2bf11eb | add carton | 2026-06-01 |
| 9d3fc23dda | fetch default packaging | 2026-05-22 |
| d21cab49ce | hide carton field unused | 2026-05-22 |
| 18a9dfffda | fix package save on item | 2026-05-20 |
| 760370a427 | fix carton qty value | 2026-05-20 |
| 2b8634c0ed | set packaging item | 2026-05-20 |
| 55a6f320d0 | setup carton view and controller | 2026-05-20 |
| 46cc4fb1d3 | add carton uom | 2026-05-20 |
| 5cd00ce59b | sync customer packaging to item | 2026-05-19 |
| 3e6fe3f0a8 | add packaging popup and validate | 2026-05-19 |
| 4e113a2a9e | add customer packaging table | 2026-05-18 |
| de76fe54d4 | add api for update packaging size | 2026-03-17 |
| ba5e05063b | sync packaging at new BOM | 2026-02-18 |
| 8ba6e5973e | add the get packaging scheduler | 2026-01-09 |

... and 37 more commits

## Affected Files

**Packaging Doctype**
- erpnext/stock/doctype/packaging/packaging.py
- erpnext/stock/doctype/packaging/packaging.json

**Packaging List Available**
- erpnext/selling/doctype/packaging_list_available/packaging_list_available.py
- erpnext/selling/doctype/packaging_list_available/packaging_list_available.json

**Packaging Material**
- erpnext/selling/doctype/packaging_material/packaging_material.py
- erpnext/selling/doctype/packaging_material/packaging_material.js
- erpnext/selling/doctype/packaging_material/packaging_material.json

**Customer Packaging**
- erpnext/selling/doctype/customer/customer.py
- erpnext/selling/doctype/customer/customer.js
- erpnext/selling/doctype/customer/customer.json
- erpnext/gp_erp/doctype/customer_packaging_detail/customer_packaging_detail.py
- erpnext/gp_erp/doctype/customer_packaging_detail/customer_packaging_detail.json

**Packing Slip (Carton & Weight)**
- erpnext/stock/doctype/packing_slip/packing_slip.py

**Item Integration**
- erpnext/stock/doctype/item/item.py
- erpnext/stock/doctype/item/item.js
- erpnext/stock/doctype/item/item.json

**Delivery Note**
- erpnext/stock/doctype/delivery_note/delivery_note.js
- erpnext/stock/doctype/delivery_note/delivery_note.json
- erpnext/stock/doctype/delivery_note_item/delivery_note_item.json

**Sales Documents**
- erpnext/selling/doctype/sales_order/sales_order.py
- erpnext/selling/doctype/sales_order/sales_order.js
- erpnext/selling/doctype/sales_order/sales_order.json
- erpnext/selling/doctype/sales_order_item/sales_order_item.json
- erpnext/selling/doctype/quotation/quotation.json
- erpnext/selling/doctype/quotation_item/quotation_item.json
- erpnext/accounts/doctype/sales_invoice/sales_invoice.js
- erpnext/accounts/doctype/sales_invoice_item/sales_invoice_item.json

**Request (Buying)**
- erpnext/buying/doctype/request/request.py
- erpnext/buying/doctype/request/request.js
- erpnext/buying/doctype/request/request.json
- erpnext/buying/doctype/request_items/request_items.json

**FOMS Integration**
- erpnext/controllers/foms.py
- erpnext/controllers/erp.py
- erpnext/controllers/erp_api.py
- erpnext/controllers/queries.py
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py

**Manufacturing**
- erpnext/manufacturing/doctype/work_order/work_order.py
- erpnext/manufacturing/doctype/work_order_item/work_order_item.json
- erpnext/manufacturing/doctype/manufacturing_settings/manufacturing_settings.json

**UOM & Conversion**
- erpnext/setup/doctype/uom/uom.json
- erpnext/stock/doctype/uom_conversion_detail/uom_conversion_detail.json
- erpnext/stock/get_item_details.py

**Print Format**
- erpnext/stock/print_format/delivery_note_(carton)/delivery_note_(carton).json

**Transaction Controller**
- erpnext/public/js/controllers/transaction.js

## Flow/Logic

### 1. Packaging Doctype
The `Packaging` doctype represents a package configuration:
- `title`: Display name (e.g., "Package (200g) - GP Type A")
- `quantity`: Package weight in source UOM
- `uom`: Unit of measure (g, kg, etc.)
- `total_weight`: Calculated weight in KG using conversion factor
- `foms_id`: External FOMS system identifier
- `package_type`: Classification of packaging type

### 2. FOMS Packaging Sync (`controllers/foms.py:get_packaging`)
Scheduled daily or triggered on-demand:
1. Fetch all Items with a `foms_product_id`
2. For each item, call FOMS API to get available packaging options
3. Create or update `Packaging` documents (`create_packaging()`)
4. Sync packaging list to Item's `packaging` child table
5. Set `default_item_pack` from existing packaging entries
6. Weight conversion: `total_weight = quantity / UOM_KG_CONVERSION_FACTOR`

### 3. Customer Packaging Preferences
Customer doctype has a `customer_packaging` child table:
- Maps item_code to preferred package type
- `validate_customer_packaging()`: Prevents duplicate (item_code, package) combinations
- When creating sales transactions, the customer's preferred packaging is auto-fetched

### 4. Packaging on Sales Flow
`get_all_product(customer)` in `customer.py`:
1. Fetches all enabled product Items (Vegetables, Herbs)
2. Joins with `Packaging List Available` to get package_item
3. Falls back to `Manufacturing Settings.default_packaging` if no specific packaging set
4. Returns item list with packaging info for order creation

### 5. Packing Slip Weight Calculation (`packing_slip.py:calculate_net_total_pkg`)
For each item in the packing slip:
1. `unit_per_carton`: Default 12 units per carton
2. `carton_weight`: Default 0.435 kg per empty carton
3. `item.cartons = ceil(qty / unit_per_carton)`
4. `item.net_weight = unit_weight * qty`
5. `item.gross_weight = net_weight + (cartons * carton_weight)`
6. `item.uom_view`: Display format as "{X} Gr" (unit_weight * 1000)
7. Totals: `net_weight_pkg`, `gross_weight_pkg`, `total_qty`

### 6. Carton UOM System
- Custom UOM type for carton-based measurement
- Carton qty is calculated from item quantity and unit_per_carton ratio
- Print format "Delivery Note (Carton)" for carton-based delivery documentation
- Filter and display logic to show/hide carton fields based on context

### 7. Request Items (Buying)
The Request document uses packaging for weight calculation:
- `unit_weight` is passed via `_add_item_to_request` to enable `total_weight` calculation
- UOM field displays packaging title (e.g., "Package (200g) - GP Type A") instead of raw UOM name
- Preview shows abbreviated format (e.g., "200 Gr")
- Total KG column follows Packaging column in the table layout

### 8. Item Packaging Integration
- Items have a `packaging` child table listing available packaging options
- `default_packaging` field for the primary package type
- Packaging syncs from FOMS when BOM is created (`sync packaging at new BOM`)
- `is_packaging_type` flag marks items that are themselves packaging materials

### 9. UOM and Packaging Trigger
- When UOM changes on a transaction line, checks if it's a packaging-type UOM
- `trigger uom or package`: Different behavior for package orders vs regular
- `skip trigger if not package order`: Avoids unnecessary recalculations
- Rate can be set per-package or per-unit depending on configuration

## Dependencies
- FOMS Integration Settings (API for packaging data)
- Manufacturing Settings (`default_packaging`, `default_fg_warehouse`)
- UOM and UOM Conversion Detail (weight conversions)
- Item doctype (packaging child table, `default_packaging` field)
- Customer doctype (`customer_packaging` child table)
- Packaging List Available (item-level packaging options)
- BOM (packaging syncs on BOM creation)

## Notes
- Weight conversion uses a `UOM_KG_CONVERSION` dictionary in `foms.py` - ensure all UOMs used have a mapping defined.
- Packing slip defaults (12 units/carton, 0.435 kg carton weight) are hardcoded - consider making these configurable per item or customer.
- The `uom_view` field shows weight in grams (unit_weight * 1000) - assumes unit_weight is always in KG.
- Customer packaging validation only checks for duplicates within the same customer - different customers can have different packaging for the same item.
- FOMS packaging sync runs on a daily scheduler (`add daily schedule to get new packaging`) and can also be triggered manually or per-item.
- Package title truncation: `doc.title = log.packageName[:159]` - titles longer than 159 chars are cut off.
