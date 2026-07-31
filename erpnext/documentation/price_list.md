# Price List Rate Validation & Notifications

## Summary
Custom enhancements to buying/selling price list defaults, item price lookup specificity, missing price notifications, price list rate validation, 4-digit item price precision, and last price list fallback logic.

## Commits
| Hash | Message | Date |
|------|---------|------|
| d3cdc08b83 | set buying price list default | 2026-07-09 |
| 15317371b6 | get item price specific | 2026-07-06 |
| e463df93a1 | create missing item price notifications | 2026-03-14 |
| 6b429a3ca8 | validate price list rate | 2025-08-08 |
| 86c2ccf721 | add 4 digits item price | 2025-05-22 |
| aaa705eed6 | change to last price list | 2025-02-12 |

## Affected Files
- erpnext/stock/get_item_details.py
- erpnext/stock/doctype/item_price/item_price.json
- erpnext/buying/doctype/buying_settings/buying_settings.json
- erpnext/controllers/buying_controller.py
- erpnext/public/js/controllers/buying.js

## Flow/Logic

### 1. Buying Price List Default (`buying_controller.py`)
1. On `onload` of a new buying document (Purchase Order, Purchase Invoice, etc.), the BuyingController checks if the document is new.
2. If `buying_price_list` field exists on the meta, it sets the value from `frappe.defaults.get_defaults().buying_price_list`.
3. Also sets `price_list_currency` from defaults.
4. This ensures new buying documents automatically use the configured default buying price list.

### 2. Get Item Price Specific (`get_item_details.py`)
1. `get_item_price(args, item_code, ignore_party=False)` queries `tabItem Price` with filters:
   - `item_code`, `price_list`, `uom` (allows blank), `batch_no` (allows blank).
   - Optionally filters by `customer` or `supplier` (unless `ignore_party=True`).
   - Filters by `transaction_date` within `valid_from` and `valid_upto` range.
2. Results ordered by `valid_from desc`, then `batch_no desc`, then `uom desc` to get the most specific/recent price.
3. `get_price_list_rate_for(args, item_code)` uses this to find the best matching price:
   - First tries party-specific (customer/supplier).
   - Falls back to general price (no party filter).
   - Falls back to stock_uom if item uom doesn't match.
   - Handles UOM conversion factor when price list is not UOM-dependent.

### 3. API-level Item Price Lookup (`erp_api.py`)
1. `get_item_price(item_code, is_selling=1, customer=None, transaction_date=None)` provides an external API.
2. Resolves price list: "Standard Selling" (is_selling=1) or "Standard Buying" (is_selling=0).
3. Resolves customer: checks if the provided name is a custom name from Forecast Settings `Subtitution Name` child table and maps to actual Customer.
4. Queries `Item Price` with filters including `valid_from <= transaction_date`, ordered by `valid_from desc`.
5. Falls back to any price if no general price found (removes customer filter).
6. Returns `{ item_code, price_list_rate, uom, price_list_name, currency }`.

### 4. Missing Item Price Notifications (`erp.py` / `erp_api.py`)
1. When a Material Request is processed and items have rate issues (missing or zero price), a notification is triggered.
2. Uses the "Material Request Rate Issue" Notification doctype to send alerts.
3. Collects items with pricing problems and sends via `notif.send(doc)`.

### 5. Price List Rate Validation (`taxes_and_totals.py` / `accounts_controller.py`)
1. During document validation, `align_price_list_rate_with_rate` ensures price list rate consistency.
2. If `price_list_rate` exists on an item:
   - Calculates rate from `price_list_rate * (1 - discount_percentage/100)`.
   - Or calculates rate as `price_list_rate - discount_amount`.
3. If rate > price_list_rate (no pricing rules), calculates margin.
4. Discount percentage is derived: `discount_amount * 100 / price_list_rate`.

### 6. 4-Digit Item Price Precision
1. The `item_price.json` schema was updated to allow 4-decimal precision for `price_list_rate`.
2. Enables more granular pricing for items requiring sub-cent precision.

### 7. Last Price List Fallback
1. When no exact price match is found for the current transaction date, the system falls back to the last valid price by ordering results by `valid_from desc`.
2. This ensures items always have a rate even if the current date falls outside explicitly defined validity windows.

## Dependencies
- Item Price doctype
- Price List doctype
- Buying Settings / Selling Settings
- Notification doctype ("Material Request Rate Issue")
- Forecast Settings (for customer name resolution in API)

## Notes
- The buying price list default is set on `onload`, not on `validate`, so it only applies to new documents.
- Party-specific pricing takes precedence over general pricing.
- The 4-digit precision change affects all Item Price records globally.
- Missing price notifications require the corresponding Notification record to be configured and enabled.
- The `ignore_party` flag in `get_item_price` allows bypassing party-specific filters for general lookups.
