# Delivery Note

## Summary
Delivery note workflow customizations including packing slip integration, custom DN types (donation, giveaway, replacement, production, marketing, pledge), internal company linking, FOMS lot tracking, non-stock item delivery, GRN validation, custom naming series, and delivery date management.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 4935101b7a | fix: validate delivery date before save, add delivery date and days to delivery in preview | 2026-07-10 |
| 642d01bb83 | fix cost center from SO SI DN | 2026-06-22 |
| 2db649fc35 | fix delivery note view | 2026-05-20 |
| 574b66b6e6 | add non-stock for delivery note | 2026-03-26 |
| da71a7e940 | validate GRN before DN | 2026-03-13 |
| b004b999ee | fix creating GRN from Delivery Note | 2026-03-13 |
| 419f468e18 | chore: enable no_copy for dn_detail and pi_detail in Packing Slip Item | 2023-04-28 |
| ddb11411ba | test: add test case for packed qty validation on DN submit | 2023-04-29 |
| ccdfca0ae8 | fix(ux): get items on selecting DN in Packing Slip | 2023-04-28 |
| 23bb7d1e23 | fix: validate Packing Slip Item Qty with DN Items | 2023-04-28 |
| bc69d29429 | fix: make DN item reference mandatory for Packing Slip Item | 2023-04-28 |
| 697e161e59 | fix: update Packed Qty in DN on submit and cancel of Packing Slip | 2023-04-28 |
| ef923f20dc | update reff row DN | 2026-02-23 |
| d6fce4e1dc | add DN controller to hooks | 2026-02-11 |
| 253c678156 | fix delivery creation and status | 2026-02-10 |
| 284b173c01 | update consignment from DN | 2026-02-10 |
| 9a7b5232aa | fix default warehouse for delivery | 2026-02-04 |
| 6a6b98e8c0 | set default warehouse delivery DN | 2026-01-22 |
| 36c42ddc3c | add marketing DN to picklist | 2026-01-21 |
| 25ed0fe39c | set only one for DN type | 2026-01-21 |
| ... and 47 more commits |

## Affected Files
**Delivery Note Core**
- erpnext/stock/doctype/delivery_note/delivery_note.py
- erpnext/stock/doctype/delivery_note/delivery_note.js
- erpnext/stock/doctype/delivery_note/delivery_note.json
- erpnext/stock/doctype/delivery_note_item/delivery_note_item.json

**Packing Slip**
- erpnext/stock/doctype/packing_slip/packing_slip.py
- erpnext/stock/doctype/packing_slip/packing_slip.js
- erpnext/stock/doctype/packing_slip/test_packing_slip.py
- erpnext/stock/doctype/packing_slip_item/packing_slip_item.json

**Delivery Term**
- erpnext/buying/doctype/delivery_term/delivery_term.py
- erpnext/buying/doctype/delivery_term/delivery_term.js
- erpnext/buying/doctype/delivery_term/delivery_term.json

**Reports**
- erpnext/foms/report/picking_list_report/picking_list_report.py
- erpnext/foms/report/picking_list_report/picking_list_report.js
- erpnext/foms/report/invoice_listing_details/invoice_listing_details.py

**Controllers**
- erpnext/controllers/erp.py
- erpnext/controllers/erp_api.py
- erpnext/controllers/foms.py
- erpnext/controllers/selling_controller.py
- erpnext/controllers/stock_controller.py

**Consignment**
- erpnext/gp_erp/doctype/consignment_request/consignment_request.py
- erpnext/gp_erp/doctype/consignment_request/consignment_request.json

**Other**
- erpnext/accounts/doctype/sales_invoice/sales_invoice.py
- erpnext/accounts/doctype/sales_invoice/sales_invoice.js
- erpnext/accounts/report/gross_profit/gross_profit.py
- erpnext/stock/doctype/batch/batch.py
- erpnext/stock/doctype/delivery_trip/delivery_trip.json
- erpnext/stock/doctype/purchase_receipt/purchase_receipt.py
- erpnext/stock/get_item_details.py
- erpnext/utilities/transaction_base.py
- erpnext/hooks.py
- erpnext/patches.txt
- erpnext/patches/v14_0/update_dn_reference_to_si.py

## Flow/Logic

### Delivery Note Validation
1. `DeliveryNote.validate()` runs in this order:
   - `validate_non_stock()` — clears warehouse for non-stock items
   - `validate_posting_time()` — standard time validation
   - Parent `SellingController.validate()` (which calls `AccountsController.validate()`)
   - `set_status()` — sets document workflow status
   - `so_required()` — checks if SO is mandatory per Selling Settings
   - `update_reff_order()` — collects SO/SI references into summary fields, fetches delivery date from SO
   - `validate_proj_cust()` — validates customer belongs to project
   - `check_sales_order_on_hold_or_close()` — prevents delivery against closed/held SOs
   - `validate_warehouse()` — ensures warehouse set for stock items
   - `validate_with_previous_doc()` — validates consistency with SO/SI (customer, company, currency, item_code, uom)
   - `validate_donation()` — sets expense accounts based on DN type
   - `validate_replacement()` — requires replacement reason
   - `add_item_batch_foms_id()` — looks up FOMS lot name from Stock Ledger Entry/Work Order
   - `validate_pledge()` — sets is_pledge=1 for "Donor" customer
   - `update_billing_status(fetch_only=True)`
   - `make_packing_list()` — builds packed items table
   - `set_batch_nos()` — assigns batch numbers for items and packed_items

### DN Type-Based Expense Account Assignment
1. `validate_donation()` checks DN type flags and assigns the appropriate expense account from Company settings:
   - `is_donation` → `donation_account`
   - `is_giveaway` → `giveaway_account`
   - `is_replacement` → `sales_replacement_account`
   - `is_production` → `production_delivery_account`
   - `is_marketing` → `marketing_delivery_account`
   - `is_pledge` → `donor_delivery_account`
2. The selected account is applied to all items' `expense_account` field.

### Packing Slip Integration
1. `PackingSlip` extends `StatusUpdater` and tracks `packed_qty` on DN Items and Packed Items.
2. `fetch_delivery_note()` pulls items from DN's `items` table (skipping Product Bundles) and `packed_items` table.
3. Each Packing Slip Item references `dn_detail` (DN Item) or `pi_detail` (Packed Item).
4. On submit/cancel, `update_prevdoc_status()` updates packed_qty on the parent DN.
5. DN submit validates packed qty via `validate_packed_qty()`.

### Internal Company Linking
1. `link_internal_company()` runs for internal customer deliveries.
2. Finds inter-company Sales Order reference from PO.
3. Locates the corresponding Purchase Receipt in the other company.
4. Sets `inter_company_reference` on both DN and PR for cross-company tracking.

### FOMS Lot Tracking
1. `add_item_batch_foms_id()` iterates all DN items with batch numbers.
2. For each batch, queries Stock Ledger Entry → Stock Entry → Work Order to find `foms_lot_name` and `foms_work_order`.
3. Falls back to `Batch.foms_lot_id` if no manufacture entry found.
4. Stores lot name and work order reference on each DN item for traceability.

### DN Submit Flow
1. `validate_packed_qty()` — ensures packing is complete before submission.
2. `validate_approving_authority()` — checks authorization for the grand total.
3. `update_prevdoc_status()` — updates delivered_qty on SO items.
4. `update_billing_status()` — syncs billing percentage.
5. `check_credit_limit()` — validates customer credit (non-return only).
6. For returns with `issue_credit_note`: calls `make_return_invoice()`.
7. `update_stock_ledger()` — posts stock ledger entries.
8. `make_gl_entries()` — creates accounting entries.
9. `clear_foms_id()` — clears FOMS ID after successful submit.
10. `set_other_reff()` — cross-links SO/SI references on DN items.

### Custom Naming Series
1. Return DNs use naming series `DO-RET-.YYYY.-.###` (set in `before_insert`).
2. Standard DN series is configurable per company.

### Delivery Date Management
1. `get_sales_order_delivery_date()` fetches delivery dates from linked Sales Orders.
2. If DN has no delivery_date set, uses the earliest SO delivery date.
3. Delivery date is validated before save (`4935101b7a`).

## Dependencies
- Sales Order (source document for delivery)
- Sales Invoice (can be source via against_sales_invoice)
- Packing Slip (packed qty tracking)
- Batch / Stock Ledger Entry / Work Order (FOMS lot tracking)
- Company settings (expense accounts for each DN type)
- Consignment Request (triggers DN creation)
- Picking List Report (references DN for warehouse picking)

## Notes
- DN types are mutually exclusive — `set only one for DN type` (`25ed0fe39c`) enforces only one flag active at a time.
- Non-stock DN (`574b66b6e6`) clears all warehouse fields, allowing delivery of service items.
- GRN validation before DN (`da71a7e940`) ensures goods receipt is completed before delivery for certain flows.
- The `status_updater` handles both normal delivery (tracking `delivered_qty`) and returns (tracking `returned_qty` and `replacement_qty`).
- `is_replacement` DN uses `-1 * qty` for SO tracking but `1 * stock_qty` for DN-to-DN tracking (special case).
- `clear_foms_id()` on submit prevents duplicate FOMS sync.
- Patch `update_dn_reference_to_si` migrates legacy DN-SI references to the new linking structure.
