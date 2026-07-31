# Print & PDF

## Summary
Custom print formats for Sales Invoice (Tax Invoice), Delivery Note, Packing Slip, Consignment Order, and SKU labels. Includes barcode generation, multi-format statement of accounts (simple/detailed), and purchase auditing voucher.

## Commits
| Hash | Message | Date |
|------|---------|------|
| eb8cde1965 | add pymupdf | 2026-06-03 |
| 612e852025 | fix print format | 2026-05-31 |
| 9deaf03ee3 | print format for consignment order | 2026-05-26 |
| ca58072e31 | packing slip print format | 2026-03-14 |
| 4385babc35 | fix print issue on quotation | 2025-12-31 |
| 9fb4eea2bb | add SKU print format | 2025-08-20 |
| 23d4deb7a7 | add reason not found pdf | 2025-08-15 |
| 7566610e99 | add create barcode function print format | 2025-02-04 |
| 351c19aaff | fix print format auditing voucher | 2024-12-09 |
| 464845be72 | add simple and detailed pdf format | 2023-09-07 |
| 0ff52e1f46 | adjust process statement printing | 2023-09-06 |
| b09cf271f6 | adjust print statement account | 2023-09-06 |
| b7fd4e25a9 | PDF Issue fixed | 2022-11-22 |

## Affected Files

### Print Format Definitions
- erpnext/accounts/print_format/greenphyto_sales_invoice_[test]/
- erpnext/accounts/print_format/tax_invoice/tax_invoice.json
- erpnext/accounts/print_format/purchase_auditing_voucher/purchase_auditing_voucher.html
- erpnext/stock/print_format/delivery_note_[test]/
- erpnext/stock/print_format/packing_slip/packing_slip.json
- erpnext/selling/print_format/sales_order_[test]/
- erpnext/gp_erp/print_format/consignment_order/consignment_order.json

### Packing Slip Format
- erpnext/stock/doctype/packing_slip/packing_slip_format.html
- erpnext/stock/doctype/packing_slip/packing_slip.json
- erpnext/stock/doctype/packing_slip/packing_slip.py
- erpnext/stock/doctype/packing_slip_item/packing_slip_item.json

### Statement of Accounts
- erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts.html
- erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts_simple.html
- erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts.js
- erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts.json
- erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts.py
- erpnext/accounts/doctype/process_statement_of_accounts_customer/process_statement_of_accounts_customer.json

### Financial Report Templates
- erpnext/accounts/report/financial_statements.html
- erpnext/accounts/report/financial_statements.py

### Consignment Order Custom Fields
- erpnext/gp_erp/custom/consignment_order.json
- erpnext/gp_erp/custom/packed_item.json
- erpnext/gp_erp/custom/sales_taxes_and_charges.json
- erpnext/gp_erp/doctype/consignment_order_item/consignment_order_item.json

### Dependencies
- pyproject.toml (pymupdf addition)

## Flow/Logic

### 1. Tax Invoice Print Format (Sales Invoice)
- Jinja-based custom print format for Sales Invoice.
- Displays: letter head, barcode of document name (via `get_barcode()` function), customer info, billing/shipping address.
- Shows item table with: item_code, tax_code, qty, UOM, rate, amount.
- Calculates tax rate from `doc.taxes[0].rate` and `item_wise_tax_detail`.
- Includes company address, TRN, and contact details in header.
- Currently disabled (`disabled: 1`) - likely superseded by newer format.

### 2. Consignment Order Print Format
- Custom Jinja print format for the Consignment Order doctype.
- Header shows: customer name, customer address, shipping address (fetched from Address doctype).
- Document details: DO No. (doc.name), date, posted date.
- Shipping address title is fetched dynamically: `frappe.db.get_value("Address", doc.shipping_address_name, "address_title")`.
- Configured with 15mm margins on all sides, font size 14.
- Module: GP ERP.

### 3. Packing Slip Print Format
- Full HTML template at `packing_slip_format.html`.
- Header sections:
  - Left: Packing Slip No, Delivery Note, Shipper (name + address), Shipper Contact, Importer (name + address), Importer Contact, Mode of Transport, Port of Loading.
  - Right: Date, Package No (from_case_no to to_case_no), Country of Origin, Destination, PO No, Incoterms, Unit per Carton, Carton Weight, Port of Discharge.
- Item table columns: No, Item Code, Qty, UOM (`uom_view`), Cartons, Net Weight, Gross Weight, Weight UOM.
- Footer: Total Net Weight, Total Gross Weight, Handling Instruction (conditional).
- Uses `frappe.utils.flt(value, 2)` for weight formatting.

### 4. Statement of Accounts (Simple & Detailed)
- Two HTML templates: `process_statement_of_accounts.html` (detailed) and `process_statement_of_accounts_simple.html` (simple).
- Generated via the Process Statement of Accounts doctype.
- Allows sending customer account statements as PDF attachments.

### 5. Barcode Generation in Print Formats
- `get_barcode()` function creates barcode images for document names.
- Used in Tax Invoice format to display scannable document barcode.
- Added in commit 7566610e99 (2025-02-04).

### 6. SKU Print Format
- Added for printing SKU labels (commit 9fb4eea2bb, 2025-08-20).
- Integrated with the Customer SKU system for product labeling.

### 7. Purchase Auditing Voucher
- HTML print format at `purchase_auditing_voucher.html`.
- Used for internal purchase audit documentation.

### 8. PyMuPDF Integration
- `pymupdf` package added to pyproject.toml for PDF manipulation.
- Enables PDF processing capabilities (merging, splitting, reading).

## Dependencies
- Frappe Print Format framework (Jinja templating)
- `get_barcode()` utility function for barcode generation
- Address doctype (dynamic address lookups in templates)
- Packing Slip doctype (custom fields: shipper, importer, port_of_loading, etc.)
- Consignment Order doctype (GP ERP custom)
- pymupdf package (PDF manipulation)
- Letter Head (company branding in prints)

## Notes
- Print formats use Jinja templating (`print_format_type: "Jinja"`) with `custom_format: 1`.
- The Tax Invoice format is currently disabled - check which format is active for Sales Invoice.
- Packing Slip format uses `uom_view` field instead of standard `uom` - this is a custom display field.
- The `[test]` suffix in some print format folder names (e.g., `greenphyto_sales_invoice_[test]`) suggests these are development/testing versions.
- Consignment Order print format fetches address title dynamically via DB call within the template.
- Statement of Accounts has two variants (simple/detailed) for different customer reporting needs.
