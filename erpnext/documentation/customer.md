# Customer

## Summary
Customer custom fields including customer code auto-generation, customer SKU management, customer packaging preferences, default address auto-fetch, cash sales designation, and internal customer handling.

## Commits
| Hash | Message | Date |
|------|---------|------|
| b18439c0d6 | fix copy customer address | 2026-05-26 |
| b3d0ae632e | add proposed customer to request | 2026-05-18 |
| 618dad6da7 | adjust customer name and allow empty before address | 2026-05-07 |
| 28e9d1e777 | fix customer warehouse | 2026-02-11 |
| 3c05ac64cb | add customer for production and marketing | 2025-10-31 |
| 52f3cc4a51 | add customer SKU | 2025-08-19 |
| a5d426d069 | add product sold by customer | 2025-07-14 |
| 968609d87d | fix calculation and add show customer | 2025-04-17 |
| b8cf20f532 | disable customer filter and filter for products | 2025-03-14 |
| c40241630b | add customer context | 2025-03-11 |
| 18a975da51 | set customer for donation | 2025-01-06 |
| 32e69bd9db | set default customer | 2024-10-24 |
| d284957eae | add customer address | 2024-09-23 |
| 3f9b7f05fe | customer code only open for new | 2024-09-11 |
| b1d8070133 | delete customer | 2024-08-30 |
| 522021035d | change ID to customer code | 2024-08-12 |
| 28a1b0dd14 | remove internal customer | 2024-08-05 |
| 905a437596 | update customer ID update | 2024-08-02 |
| 1ba75a5649 | add customer internal | 2024-07-31 |
| a72c9ebbe7 | cannot use code for another customer | 2024-07-31 |
| 636663f522 | add customer internal | 2024-07-31 |
| 68d91f60fd | sync all customer | 2024-06-28 |
| bc1573a434 | get customer currency | 2024-06-06 |
| 7685f3446a | filter customer for debit note | 2024-03-04 |
| cff1dd8429 | create customer | 2024-01-25 |
| 39fe55e95b | set customer code | 2023-09-12 |
| a8ca276d81 | revert customer id | 2023-09-12 |

## Affected Files

### Core Customer
- erpnext/selling/doctype/customer/customer.py
- erpnext/selling/doctype/customer/customer.js
- erpnext/selling/doctype/customer/customer.json

### Customer SKU
- erpnext/foms/doctype/customer_sku/__init__.py
- erpnext/foms/doctype/customer_sku/customer_sku.json
- erpnext/foms/doctype/customer_sku/customer_sku.py

### Reports
- erpnext/foms/report/product_sold_by_customer/
- erpnext/foms/report/batch_delivery/
- erpnext/foms/report/distribution_by_stores/

### Related Controllers
- erpnext/controllers/erp.py
- erpnext/controllers/erp_api.py
- erpnext/controllers/foms.py
- erpnext/accounts/party.py
- erpnext/accounts/custom/address.py

### Patches
- erpnext/patches/v14_0/add_internal_customer.py
- erpnext/patches/v14_0/revert_customer_name.py

## Flow/Logic

### 1. Customer Code Auto-Generation (`set_code()`)
- On autoname, after setting the customer name, `set_code()` generates a unique customer code.
- Format: `{company_series_abbr}C.#####` (e.g., "GPC00001").
- Cash sales customers get a fixed code: `{company_series_abbr}C00008`.
- If a customer_code is manually set, validates uniqueness across all customers.
- Called during both `autoname()` and `validate()` to ensure code is always set.

### 2. Customer SKU Management (`validate_sku()`)
- Customers have a `customer_sku` child table mapping items to customer-specific SKU codes.
- Validates no duplicate item_code entries in the SKU table.
- Validates no duplicate SKU numbers.
- Auto-sets `sku_name` from `origin_name` if not provided.
- Tracks `total_item` count.
- `get_item_sku(item_code, field)` helper retrieves SKU or SKU name for a given item.

### 3. Customer Packaging Preferences
- `customer_packaging` child table stores per-item packaging preferences.
- Each row has: item_code, item_name, package, packaging, carton_uom, carton_size.
- `validate_customer_packaging()` checks for duplicate (item_code, package) combinations.
- JS `get_all_product` button opens a dialog to select products from available items, with checkboxes showing existing selections.
- `update_carton_size` button bulk-updates all packaging rows to the `default_carton_size` value.
- Filters: item_code limited to "Products" item_group, carton_uom to `is_carton` UOMs, packaging to "Other Packaging" material_group, package to `is_packaging` UOMs.

### 4. Default Customer Address Auto-Fetch (`set_default_customer_address()`)
- During validation, if `customer_primary_address` is not set, queries all addresses linked to the customer.
- Takes the first address found, renders it using the address template, and sets both `customer_primary_address` and `primary_address` display fields.

### 5. Cash Sales Customer (JS)
- `is_cash_sales` toggle fetches company `series_abbr` and sets customer_code to the fixed cash sales code.
- Toggling off clears the customer_code for regeneration.

### 6. Internal Customer Validation
- `validate_internal_customer()`: Ensures only one internal customer exists per `represents_company`.
- Clears `represents_company` if `is_internal_customer` is unchecked.

### 7. Customer Name Auto-Naming
- Supports three modes via global default `cust_master_name`:
  - "Customer Name": uses customer_name directly, appending a counter if duplicate.
  - "Naming Series": uses standard naming series.
  - Otherwise: uses the doctype's autoname option.

### 8. Customer Packaging Dialog (JS)
- `get_all_product` calls `erpnext.selling.doctype.customer.customer.get_all_product` to fetch available products.
- Renders a dialog with a table of all products, marking existing rows as checked.
- On save: adds newly checked rows, prompts for confirmation before deleting unchecked existing rows.
- Each new row defaults carton_uom to "Carton" and carton_size to `default_carton_size` or 12.
- Validates uniqueness of (item_code, package) combination on both client and server side.

## Dependencies
- Company doctype (`series_abbr` field for customer code generation)
- Address doctype (customer primary address linking)
- FOMS Integration Settings (customer sync)
- Customer SKU child doctype
- Customer Packaging Detail child doctype
- Item doctype (item_group filters for packaging)
- UOM doctype (is_carton, is_packaging flags)

## Notes
- Customer code uniqueness is enforced at validation time - if a code is already used by another customer, a validation error is thrown.
- The `set_code()` method is called both in `autoname()` and `validate()`, ensuring codes are set for both new and existing records.
- Customer packaging validation prevents the same item+package combination from being added twice.
- The `get_item_sku` method falls back to `origin_name` if `sku_name` is empty but SKU exists.
- Cash sales customers have a reserved code pattern ending in "C00008".
