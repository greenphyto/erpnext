# Bulk Upload Forecast

## Summary
Bulk CSV upload dialog with preview, editable DataTable, and auto submit for the Request doctype. Allows users to upload forecast CSV files from the Forecast Settings page, parse and validate item/customer mappings, preview grouped data in an editable table, and generate Request documents in bulk.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 3f89442b8a | feat: add auto submit checkbox in bulk upload dialog | 2026-07-10 |
| 9dcc0423a2 | fix: XSS prevention and edits re-keying after group deletion in bulk upload | 2026-07-10 |
| 238966097c | feat: add bulk upload dialog with CSV preview and editable DataTable | 2026-07-10 |
| de81b1d7b1 | feat: add generate_bulk_requests method for bulk CSV upload | 2026-07-10 |
| 9eb8463489 | fix: add customer validation, date validation, and zero-qty handling to parse_forecast_upload | 2026-07-10 |
| 2967f9dcf2 | feat: add parse_forecast_upload method for bulk CSV upload | 2026-07-10 |

## Affected Files
- erpnext/buying/doctype/request/request.js
- erpnext/buying/doctype/request/request.py
- erpnext/gp_erp/doctype/forecast_settings/forecast_settings.js
- erpnext/gp_erp/doctype/forecast_settings/forecast_settings.json
- erpnext/gp_erp/doctype/forecast_settings/forecast_settings.py

## Flow/Logic

### 1. CSV Upload & Parsing (`parse_forecast_upload`)
1. User uploads a CSV file via the Forecast Settings UI.
2. The CSV must contain columns: `Delivery Date`, `Customer`, `Vegetable`, `Predicted Packages`, `UOM (g)`, `Predicted Kg`, `Unit Price (SGD)`.
3. `parse_forecast_upload` is called with the raw CSV content.
4. Forecast Settings document is loaded (must be enabled).
5. For each row:
   - Validates delivery date format (skips invalid).
   - Resolves `Customer` custom name to actual Customer via `_resolve_customer` using Forecast Settings `customers` child table.
   - Resolves `Vegetable` to `item_code` via `_resolve_item` using Forecast Settings `items` child table.
   - Resolves packaging by matching weight (grams converted to kg) against the item's `Packaging List Available` child table.
   - Gets item rate from Item Price (selling price list) or falls back to CSV `Unit Price (SGD)`.
   - Skips rows with zero or missing `Predicted Packages`.
6. Valid rows are grouped by `(delivery_date, customer)`.
7. Returns `{ groups: [...], warnings: [...], summary: { total_groups, total_items } }`.

### 2. Preview & Edit (Client-side Dialog)
1. The Forecast Settings JS opens a dialog with an editable DataTable showing the grouped items.
2. Users can edit quantities in the table before confirming.
3. An "Auto Submit" checkbox allows automatic submission of created Requests.
4. XSS prevention sanitizes displayed values; edits are re-keyed correctly after group deletion.

### 3. Bulk Request Generation (`generate_bulk_requests`)
1. Called with the parsed `groups` data and optional `edits` dict `{group_idx: {item_idx: {qty: new_qty}}}`.
2. Applies quantity edits to items.
3. For each group:
   - Validates delivery date is not in the past.
   - Checks for an existing draft Request with same `proposed_customer` and `delivery_date` via `_get_existing_request`.
   - If existing: updates/merges items using `_add_item_to_request` (replaces qty if item exists, appends if new).
   - If new: creates a new Request with company/department from Forecast Settings defaults.
4. Saves and optionally submits (if `auto_submit=1`) new Requests.
5. Adds comments tracking creation/update via Forecast API.
6. Returns `{ created: [...], merged: [...], errors: [...], summary: "X created, Y merged, Z errors" }`.

### Helper Functions
- `_resolve_item(veg_name, settings)`: Maps custom vegetable name to item_code from Forecast Settings items table.
- `_resolve_customer(customer_name, settings)`: Maps custom customer name to Customer from Forecast Settings customers table.
- `_resolve_packaging(item_code, uom_in_kg)`: Finds packaging from Item's `packaging_list_available` by weight, returns packaging item and name.
- `_get_item_price(item_code)`: Gets rate from Item Price for the default selling price list.
- `_get_existing_request(customer, delivery_date)`: Checks for existing draft Request with same customer and delivery date.
- `_add_item_to_request(doc, item_data)`: Adds or updates item row in Request; returns change info.

## Dependencies
- Forecast Settings doctype (with `enable`, `items`, `customers`, `company_default`, `department_default` fields)
- Request doctype
- Item Price / Selling Settings
- Packaging / Packaging List Available

## Notes
- Customer and vegetable names in the CSV must match `custom_name` entries in the Forecast Settings child tables.
- If packaging is not found for an item/weight combination, a warning is returned but the item is still included.
- Zero-qty rows are skipped with a warning.
- Delivery dates in the past are rejected during `generate_bulk_requests`.
- The `auto_submit` flag only applies to newly created Requests, not merged ones.
