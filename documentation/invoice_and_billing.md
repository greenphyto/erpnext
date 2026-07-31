# Invoice & Billing

## Summary
Custom invoice validation, over-billing prevention, tax handling, AI-powered invoice extraction, sales/purchase invoice customizations, consignment invoicing, internal company invoice linking, and custom reports (invoice listing, item price, WIP account detail).

## Commits
| Hash | Message | Date |
|------|---------|------|
| 5e091693d8 | fix over billing issue | 2026-06-29 |
| 2792041f80 | add validation invoice text | 2026-06-10 |
| 9e39d0835e | sales invoice and stock for consignment | 2026-05-25 |
| 7fd6b1f97e | adjust sales invoice | 2026-05-21 |
| bec9a19500 | fixing trade creditors invoice | 2026-04-24 |
| 95a5972582 | filter company on invoice | 2026-04-16 |
| 7ae4e5be2c | get net amount per invoice | 2026-04-07 |
| 756fcb21c8 | fix name error when has more invoices | 2026-03-04 |
| 4ee59afc97 | add selected invoice | 2026-02-26 |
| b996fea446 | sync sales invoice creation | 2026-02-11 |
| b2af3a009d | create delivery note and sales invoice | 2026-02-09 |
| cf4b409574 | set address shipping based on billing for internal | 2026-01-22 |
| 54379a7ddf | total amount view on get invoices | 2026-01-19 |
| c585b1563d | fix invoice filters | 2026-01-13 |
| 7b0470ab32 | add new sales invoice price | 2025-12-22 |
| 5d672f7771 | change price source only from Sales Invoice | 2025-12-19 |
| cd17dcb316 | fix linked invoice from internal company | 2025-12-16 |
| c20eb5de0c | add manual trigger notification invoice | 2025-12-03 |
| 9efd4ec302 | ai: rename after submit purchase invoice | 2025-10-31 |
| 178261bb01 | ai; save multiple result invoice | 2025-10-09 |
| ... and 42 more commits |

## Affected Files
**Core Invoice Logic**
- erpnext/accounts/doctype/sales_invoice/sales_invoice.py
- erpnext/accounts/doctype/sales_invoice/sales_invoice.json
- erpnext/accounts/doctype/sales_invoice_item/sales_invoice_item.json
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.py
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.js
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.json
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice_list.js
- erpnext/controllers/accounts_controller.py

**AI Invoice Processing**
- erpnext/ai_agent/doctype/ai_agent_settings/ai_invoice_converter.py
- erpnext/ai_agent/doctype/email_invoice/email_invoice.py
- erpnext/ai_agent/doctype/email_invoice/email_invoice.json
- erpnext/ai_agent/doctype/email_invoice_result/email_invoice_result.py
- erpnext/ai_agent/doctype/email_invoice_result/email_invoice_result.json
- erpnext/controllers/ai.py

**Reports**
- erpnext/foms/report/invoice_listing_details/invoice_listing_details.py
- erpnext/foms/report/invoice_listing_details/invoice_listing_details.js
- erpnext/foms/report/item_price_and_invoice/item_price_and_invoice.py
- erpnext/foms/report/sales_invoice_price/sales_invoice_price.py
- erpnext/foms/report/wip_account_detail/wip_account_detail.py

**Notifications**
- erpnext/foms/notification/new_purchase_invoice_from_ai_agent/
- erpnext/foms/notification/submit_invoice_draft/

**UOB Payment Integration**
- erpnext/uob/doctype/payment_approval/payment_approval.py
- erpnext/uob/doctype/payment_approval/payment_approval.js
- erpnext/uob/doctype/payment_invoice_list/payment_invoice_list.json
- erpnext/uob/page/payment_bulk_approval/payment_bulk_approval.js

**Consignment**
- erpnext/gp_erp/doctype/consignment_request/consignment_request.py
- erpnext/gp_erp/doctype/consignment_request/consignment_request.json
- erpnext/gp_erp/doctype/consignment_request_item/consignment_request_item.json

**Other**
- erpnext/accounts/doctype/gl_entry/gl_entry.py
- erpnext/accounts/doctype/accounts_settings/accounts_settings.json
- erpnext/controllers/erp.py
- erpnext/controllers/uob.py
- erpnext/public/js/controllers/transaction.js
- erpnext/public/js/utils.js
- erpnext/hooks.py
- erpnext/patches/trade_creditors_issue/app.py

## Flow/Logic

### Sales Invoice Validation
1. `SalesInvoice.validate()` calls `validate_item_price_list()` first to ensure item prices are valid.
2. Parent `SellingController.validate()` is called which triggers `AccountsController.validate()`.
3. `AccountsController.validate()` runs `validate_qty_is_not_zero()` (skips returns/debit notes), sets missing values, validates fiscal year, calculates taxes and totals, and validates base_grand_total >= 0.
4. Over-billing is prevented via `status_updater` which tracks `billed_amt` against `Sales Order Item` with `overflow_type: "billing"`.

### Purchase Invoice Validation
1. `PurchaseInvoice.validate()` validates posting time, calls parent `BuyingController.validate()`.
2. For non-return invoices: validates PO required (`po_required()`), PR required (`pr_required()`), and supplier invoice number (`validate_supplier_invoice()`).
3. The `status_updater` tracks `billed_amt` against `Purchase Order Item` with `overflow_type: "billing"` to prevent over-billing.

### AI Invoice Extraction
1. Emails with invoices are captured via `email_invoice` doctype.
2. `ai_invoice_converter.py` processes attachments using AI to extract invoice data.
3. Results are saved to `email_invoice_result` child table (supports multiple results per email).
4. On successful extraction, a Purchase Invoice is created and renamed after submit.
5. Notifications are sent via "New Purchase Invoice from AI Agent" notification template.

### Internal Company Invoice Linking
1. For inter-company transactions, `set_inter_company_account()` is called during validation.
2. Shipping address is set based on billing address for internal transfers (`cf4b409574`).
3. Linked invoices from internal companies are properly resolved (`cd17dcb316`).

### Invoice Reminder (Draft Submit)
1. `reminder_submit_invoice()` in `controllers/erp.py` runs on the last day of each month.
2. Queries all draft Sales Invoices (`docstatus=0`) with posting_date <= end of current month.
3. Sends notification via "Submit Invoice Draft" notification template.

### Cost Center Assignment
1. `AccountsController.set_cost_center_by_settings()` runs for Sales Invoice, Delivery Note, Purchase Order, Purchase Invoice, Purchase Receipt.
2. For each item, it gets the cost center from the income/expense account via `get_cost_center_from_account()`.
3. If the cost center is "locked" in settings, it overrides; otherwise it sets as default.

### Consignment Invoicing
1. Consignment requests can trigger Sales Invoice and stock movements (`9e39d0835e`).
2. The flow links consignment items to invoice items for tracking.

## Dependencies
- Accounts Controller (`erpnext/controllers/accounts_controller.py`)
- AI Agent module (`erpnext/ai_agent/`)
- UOB Payment module (`erpnext/uob/`)
- FOMS Integration (`erpnext/controllers/foms.py`)
- Consignment Request (`erpnext/gp_erp/doctype/consignment_request/`)
- Notification framework (Frappe)

## Notes
- Over-billing validation uses `overflow_type: "billing"` in `status_updater` — this is the standard ERPNext mechanism extended with GP customizations.
- The AI invoice converter renames the Purchase Invoice after submit to match a custom naming convention.
- Trade creditors issue fix (`bec9a19500`) has a dedicated patch under `erpnext/patches/trade_creditors_issue/`.
- Company filter on invoices ensures users only see invoices for their assigned company.
- `validate_item_price_list()` is a GP-custom method added to Sales Invoice validation before the standard flow.
- The `before_print` hook in `AccountsController` adds SKU and UOM display names for printed invoices.
