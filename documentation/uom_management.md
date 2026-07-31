# UOM Default & Conversion Management

## Summary
Custom UOM handling that includes: default UOM auto-population on items, UOM conversion factor overrides on the Item doctype, FOMS-to-ERP UOM mapping, UOM filtering specific to items in transactions, and allowing stock UOM changes when quantity is zero.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 6123c7a608 | add default UOM | 2026-07-07 |
| 88da65dd83 | add get uom list | 2026-07-06 |
| 1df8f781d1 | fix: copy correct uom from delivery note when creating packing list | 2025-02-03 |
| 25848b87cd | filter uom specific to item | 2025-11-07 |
| fc2f473d29 | Revert "advancing UOM conversion V2" | 2025-08-20 |
| 5bc19a06da | advancing UOM conversion V2 | 2025-08-20 |
| fe1d3264b1 | fix different uom finish goods | 2024-09-12 |
| f76909537f | keep quantity but different uom | 2024-09-12 |
| 74358157c2 | add uom convertion auto | 2024-09-12 |
| c7923b11a4 | add overide uom value | 2024-09-10 |
| dff784c1ea | add controller uom detail | 2024-09-09 |
| 9ff2b5c09c | change stock uom warning messages | 2024-09-09 |
| 373ced42d5 | fix display uom | 2024-09-03 |
| 6f89b4d968 | filter uom based on item | 2024-08-05 |
| 93864ebb7f | change back to uom field | 2024-08-05 |
| bc8cd21a79 | show uom convertion | 2024-05-21 |
| e77d4b582b | allow change stock uom if zero qty | 2024-03-22 |
| a4187b9d8f | fix: set stock UOM in args to ensure item price is fetched | 2022-11-09 |
| 92b9d3dc6d | test: validate qty and purchase uom in material request from PP | 2022-10-19 |

## Affected Files
**Item Doctype**
- erpnext/stock/doctype/item/item.py
- erpnext/stock/doctype/item/item.js
- erpnext/stock/doctype/item/item.json

**UOM Conversion Detail**
- erpnext/stock/doctype/uom_conversion_detail/uom_conversion_detail.json

**Item Details (get_item_details)**
- erpnext/stock/get_item_details.py

**Transaction Controllers**
- erpnext/public/js/controllers/transaction.js
- erpnext/public/js/queries.js

**FOMS Integration**
- erpnext/controllers/foms.py (UOM_MAP, get_uom function)
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py

**Document-specific**
- erpnext/stock/doctype/delivery_note/delivery_note.py
- erpnext/stock/doctype/delivery_note/delivery_note.js
- erpnext/stock/doctype/packing_slip/packing_slip.py
- erpnext/stock/doctype/stock_entry/stock_entry.py
- erpnext/selling/doctype/sales_order/sales_order.py
- erpnext/selling/doctype/sales_order/sales_order.js
- erpnext/buying/doctype/request/request.py
- erpnext/buying/doctype/request/request.js
- erpnext/accounts/doctype/sales_invoice/sales_invoice.js

**API**
- erpnext/controllers/erp_api.py
- erpnext/www/swagger/api.json

## Flow/Logic

### Default UOM on Item
1. When an Item is saved, `add_default_uom_in_conversion_factor_table()` ensures the stock_uom is present in the item's UOM conversion table with conversion_factor = 1.
2. If stock_uom changes, the UOM conversion table is cleared and user is prompted to redefine conversion factors.
3. Stock UOM change is allowed only when the item has zero stock quantity (GP customization over standard which blocks all changes).

### UOM Conversion Detail (Custom Fields)
The `UOM Conversion Detail` child table has GP custom fields:
- `to_uom`: Target UOM for the conversion.
- `cf_view`: Display-friendly conversion factor.
- `is_packaging`: Fetched from UOM, indicates packaging unit.
- `is_carton`: Carton flag.
- `global_description`, `description`, `origin_description`: Descriptive fields.
- `reff_id`: Reference ID for external systems.

### UOM Filtering in Transactions
1. When selecting UOM in transaction items (Sales Order, Purchase Order, etc.), the UOM dropdown is filtered to only show UOMs defined in that item's conversion table.
2. This prevents users from selecting UOMs that have no defined conversion factor for the item.
3. Implemented via `get_query` filters in JS controllers that restrict the UOM Link field.

### FOMS UOM Mapping
1. `UOM_MAP` in `controllers/foms.py` maps FOMS unit codes to ERPNext UOM names:
   - L -> Litre, g -> Gram, kg -> Kg, unit -> Unit, ml -> Millilitre
2. `UOM_MAP_REV` provides the reverse mapping for ERP-to-FOMS sync.
3. `get_uom(uom_foms, default)` function resolves a FOMS UOM code to an ERPNext UOM name, falling back to checking if it exists as an Item, then throwing an error if not found.

### UOM in get_item_details
1. When fetching item details for a transaction line, the stock_uom is set in args to ensure correct item price lookup.
2. Conversion factor is calculated based on the selected UOM vs stock_uom from the item's conversion table.
3. `get_uom_conv_factor` (from item.py) retrieves the conversion factor for a given UOM pair.

### Packing Slip UOM
1. When creating a Packing Slip from a Delivery Note, the correct UOM is copied from the DN item (fix for cases where wrong UOM was being transferred).

### Stock Entry UOM
1. For finished goods in manufacturing Stock Entries, handles cases where the BOM item has a different UOM than the stock UOM, maintaining quantity while converting units.

## Dependencies
- Item doctype (uoms child table - UOM Conversion Detail)
- UOM doctype (is_packaging field)
- FOMS Integration Settings
- get_item_details (stock module)
- Transaction controller (public/js)

## Notes
- "Advancing UOM conversion V2" was committed and then immediately reverted, suggesting the feature was not stable.
- The `cf_view` field on UOM Conversion Detail appears to be a display-only calculated field showing the conversion in human-readable format.
- The `is_packaging` and `is_carton` flags enable special logic for packaging-related UOM conversions (used in packing slips and FOMS sync).
- When filtering UOMs in transactions, if the item has no UOM conversions defined, the filter falls back to showing all UOMs.
- The `allow change stock uom if zero qty` commit relaxes the standard ERPNext restriction that completely prevents stock UOM changes after creation.
