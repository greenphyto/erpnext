# Forecast Settings & Lead Time Sync

## Summary
A singleton Settings doctype that maps external vegetable/customer names to ERPNext Item/Customer records. Provides API endpoints for receiving forecast data from external systems and creating/updating Request documents automatically.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 6f1114aa13 | add request to create forecast | 2026-07-01 |
| a1c1510d9f | init forecast settings | 2026-06-30 |

## Affected Files
- erpnext/gp_erp/doctype/forecast_settings/__init__.py
- erpnext/gp_erp/doctype/forecast_settings/forecast_settings.js
- erpnext/gp_erp/doctype/forecast_settings/forecast_settings.json
- erpnext/gp_erp/doctype/forecast_settings/forecast_settings.py
- erpnext/gp_erp/doctype/subtitution_name/__init__.py
- erpnext/gp_erp/doctype/subtitution_name/subtitution_name.json
- erpnext/gp_erp/doctype/subtitution_name/subtitution_name.py
- erpnext/buying/doctype/request/request.py
- erpnext/controllers/erp_api.py

## Flow/Logic
1. **Forecast Settings Doctype** (Single):
   - Fields: `enable` (Check), `forecast_days` (Int, default 30), `company_default` (Link to Company), `department_default` (Link to Department).
   - Child tables: `items` (Table of Subtitution Name, mapping custom_name → Item) and `customers` (Table of Subtitution Name, mapping custom_name → Customer).
   - JS sets query filters: items filtered to `item_group="Products"`, customers filtered to non-disabled in default company.

2. **Name Resolution** (in `request.py`):
   - `_resolve_item(veg_name, settings)`: Iterates `settings.items` to find row where `custom_name == veg_name` and `ref_doctype == "Item"`, returns `ref_name`.
   - `_resolve_customer(customer_name, settings)`: Same pattern for `settings.customers` with `ref_doctype == "Customer"`.
   - `_resolve_packaging(item_code, uom_in_kg)`: Finds matching packaging from Item's `packaging_list_available` child table by weight.

3. **Lead Time API** (`erp_api.py` → `get_lead_time`):
   - Whitelisted endpoint accepting `veg_names` (list of custom vegetable names).
   - Calls `get_lead_time_by_custom_names()` in `request.py` which resolves each name to item_code, then fetches `lead_time_days` from Item master.
   - Returns `{min_lead_time, max_lead_time, detail: {name: days}}`.

4. **Receive Forecast API** (`erp_api.py` → `receive_forecast`):
   - Accepts array of objects with `veg_name`, `packages`, `uom_in_kg`, `forecast_date`, `customer`.
   - Validates required fields, resolves customer/item/packaging via Forecast Settings.
   - Groups items by `(customer_name, forecast_date)`.
   - Calls `create_or_update_forecast_request()` for each group.

5. **Request Creation** (`request.py` → `create_or_update_forecast_request`):
   - Checks for existing draft Request with same customer + delivery_date (`_get_existing_request`).
   - If exists: updates items (replaces qty if item_code already present, adds new rows otherwise).
   - If not exists: creates new Request with company/department from settings.
   - Adds comment documenting the changes (new items, qty changes).

6. **Bulk Upload** (`request.py` → `parse_forecast_upload` + `generate_bulk_requests`):
   - `parse_forecast_upload`: Parses CSV content with columns (Delivery Date, Customer, Vegetable, Predicted Packages, UOM (g), etc.), maps all fields via settings, groups by (delivery_date, customer).
   - `generate_bulk_requests`: Creates/merges Requests from grouped data, supports inline edits to qty, and optional auto-submit.

## Dependencies
- Subtitution Name child doctype (shared for items and customers mapping)
- Request doctype
- Item master (lead_time_days, packaging_list_available)
- Packaging doctype
- Selling Settings / Stock Settings (for price list)
- erp_api.py controller

## Notes
- Settings must have `enable` checked; otherwise API calls throw an error.
- The `Subtitution Name` child doctype uses `ref_doctype` + `ref_name` pattern (Dynamic Link style).
- CSV upload validates columns strictly and collects warnings for unmapped items/customers without blocking entire upload.
- Existing draft Requests are merged (not duplicated) when same customer + delivery_date match.
