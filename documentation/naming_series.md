# Naming Series

## Summary
Custom naming series patterns across multiple doctypes, company-specific numbering, autoname overrides for BOM/Work Order/Job Card, part number management system with material group-based sequential numbering, bank number field management for UOB integration, and document series mapping between related documents (MR→PO, SO→DO, etc.).

## Commits

### Initial Series Customization (2022-2023)
| Hash | Message | Date |
|------|---------|------|
| fff9e76718 | fix: number of months subscription plan | 2022-10-10 |
| 81f2189121 | change series | 2023-09-05 |
| 798f15286f | add more series | 2023-09-21 |
| 0077426724 | change series by account map | 2023-09-27 |
| 79ff4b6cd8 | mapping series from MR to PO | 2023-10-12 |
| e4bbed94bc | remove selected po series | 2023-10-13 |
| 4bfc94d91c | auto select series | 2023-11-02 |
| 06748a7108 | change series auto | 2023-11-08 |
| c6856cce5a | remove standard series | 2023-11-15 |
| 54ce07d499 | remove number when export | 2023-12-07 |

### Material/Part Number System (2024)
| Hash | Message | Date |
|------|---------|------|
| a579cc1141 | add material group number | 2024-01-03 |
| 37452057ab | add account number | 2024-04-04 |
| 682869ba98 | add against account number | 2024-04-04 |
| d53bc865a2 | update current material number | 2024-07-16 |
| 8434723add | new part number based on patch | 2024-07-22 |
| f5e1edde4c | add new part number | 2024-07-31 |
| ec6b44f8b7 | add new part number | 2024-08-07 |
| 4e605d45bf | add accessories part number | 2024-08-07 |
| bb9608829e | make part number settings | 2024-09-23 |
| 97a1dec483 | mapping part number based on settings | 2024-09-24 |
| 5746fb1f5f | parse number series | 2024-09-24 |

### Credit Note & PO Series (2024-2025)
| Hash | Message | Date |
|------|---------|------|
| 881d132b35 | add series to credit note | 2024-12-19 |
| 926bdfe575 | update PO number by SO | 2025-02-20 |
| f229b3ceb8 | auto series when return | 2025-02-28 |
| 9985426f70 | fix series issues | 2025-03-03 |
| b90a42a304 | fix PO number error | 2025-04-30 |

### Bank Number System (2025)
| Hash | Message | Date |
|------|---------|------|
| 46752a9697 | add bank number | 2025-05-20 |
| cd99ccfa92 | add bank number field | 2025-09-10 |
| 97f5e538ff | add bank number details | 2025-09-10 |
| 798606bf41 | uob: validate bank number | 2025-11-13 |
| 943b5350d3 | uob: validate account number digit | 2025-11-12 |

### Company-Specific Series (2025-2026)
| Hash | Message | Date |
|------|---------|------|
| eb3142ac20 | set series for GPM and GPO | 2025-10-27 |
| 21338c2d4b | prod: update series | 2025-10-31 |
| fa0094344e | fix naming series from donor SO to DO | 2026-02-05 |
| 272daae2e5 | change naming series name | 2026-04-21 |
| 26bad8eb66 | abbreviation on naming series | 2026-04-22 |
| 58bd67ed76 | fix series add consignment | 2026-05-31 |

... and 52 more commits

## Affected Files

**Part Number Settings (Custom Doctype):**
- erpnext/accounts/doctype/part_number_settings/part_number_settings.js
- erpnext/accounts/doctype/part_number_settings/part_number_settings.json
- erpnext/accounts/doctype/part_number_settings/part_number_settings.py
- erpnext/accounts/doctype/part_number_details/part_number_details.json

**Bank Number (Custom Doctype):**
- erpnext/accounts/doctype/bank_number/bank_number.py
- erpnext/accounts/doctype/bank_number/bank_number.js
- erpnext/accounts/doctype/bank_number/bank_number.json

**Material Group:**
- erpnext/accounts/doctype/material_group/material_group.js
- erpnext/accounts/doctype/material_group/material_group.json

**Item Naming:**
- erpnext/stock/doctype/item/item.py
- erpnext/stock/doctype/item/item.js
- erpnext/stock/doctype/item/item.json
- erpnext/stock/__init__.py

**Document Series (JSON configs):**
- erpnext/selling/doctype/sales_order/sales_order.json
- erpnext/selling/doctype/quotation/quotation.json
- erpnext/buying/doctype/purchase_order/purchase_order.json
- erpnext/stock/doctype/delivery_note/delivery_note.json
- erpnext/stock/doctype/material_request/material_request.json
- erpnext/stock/doctype/purchase_receipt/purchase_receipt.json
- erpnext/manufacturing/doctype/work_order/work_order.json
- erpnext/manufacturing/doctype/job_card/job_card.json
- erpnext/accounts/doctype/sales_invoice/sales_invoice.json
- erpnext/accounts/doctype/purchase_invoice/purchase_invoice.json
- erpnext/accounts/doctype/journal_entry/journal_entry.json
- erpnext/accounts/doctype/payment_entry/payment_entry.json
- erpnext/assets/doctype/asset/asset.json

**Controllers:**
- erpnext/controllers/erp.py
- erpnext/controllers/erp_api.py
- erpnext/controllers/sales_and_purchase_return.py
- erpnext/controllers/accounts_controller.py
- erpnext/controllers/uob.py
- erpnext/controllers/pdf_utils.py

**GL & Reports:**
- erpnext/accounts/doctype/gl_entry/gl_entry.py
- erpnext/accounts/report/general_ledger/general_ledger.py
- erpnext/accounts/report/balance_sheet/balance_sheet.py

## Flow/Logic

### Material Number Assignment (Item)
1. On item validate, `set_material_number()` checks if `material_group` is set
2. If set, calls `parse_material_group_series(material_group)` to build a naming series
3. Material Group doctype stores `number_start` and `number_end` (e.g., 1000, 1999)
4. Series pattern is constructed: diff = end - start, builds pattern like `10.####`
5. Uses frappe's `parse_naming_series()` to generate next sequential number
6. Item code prefix determines material group via `get_item_material_group()`:
   - `RM-SD` → Seeds (10.####)
   - `RM-NS` → Nutrition (11.####)
   - `PR-LV` → Vegetables (Lettuce) (14.####)
   - `PDLED` → LED (20.####)
   - `PD-` → Trays & Boards (27.####)
   - etc.

### Part Number Settings
1. Company-level doctype that maps item codes/part numbers to GL accounts
2. `data_mapping` child table contains: code, part_number, account_code, account_currency
3. Used by `get_warehouse_account_map()` to override default warehouse accounts per item
4. Access restricted via custom permissions (`limit access for part number settings`)

### BOM Autoname
1. Pattern: `BOM-{item_code}-{operation_no}{version_index}`
2. Finds existing BOMs matching pattern, extracts max index, increments
3. Version index zero-padded to 3 digits

### Work Order Autoname
1. If `operation_no` set: maps to alpha (1→A, 2→B, etc.)
2. Base is `foms_lot_name` or `naming_series`
3. Pattern: `{base}-.###.-{alpha}` or `{base}-.###`

### Job Card Series
1. Custom naming series set in job_card.json
2. Updated to match GP conventions (commit 88fff192a6)

### Series Mapping Between Documents
1. MR → PO: naming series from Material Request carries to Purchase Order
2. SO → DO: donor SO naming maps to Delivery Note series
3. Return documents: auto-series applied when creating return entries
4. Credit notes: dedicated series for credit note invoices

### Bank Number System
1. Bank Number is a custom doctype for UOB payment integration
2. Stores account numbers with validation (digit count, PayNow format)
3. `validate_bank_number()` checks format based on bank type
4. Country auto-set based on bank number prefix
5. Draft bank number assigned on creation of new payment entries

### GL Entry Account Number
1. `against_account` field in GL Entry stores account numbers
2. Account number added to GL entries for reporting clarity
3. Balance sheet and P&L reports can filter/display by account number

### Company Abbreviation in Series
1. Series patterns use company abbreviation (GPM, GPO) for multi-company setup
2. `abbreviation on naming series` commit adds company prefix to document names
3. Consignment orders get dedicated series

## Dependencies
- Material Group (doctype with number_start/number_end for series generation)
- Part Number Settings (company-level account mapping)
- FOMS Integration (lot names used as WO naming base)
- UOB Integration (bank number validation and payment flow)
- Company (abbreviation used in series patterns)
- frappe.model.naming (parse_naming_series, getseries core functions)

## Notes
- Standard ERPNext naming_series is preserved for most doctypes but with GP-specific options
- Material number is distinct from item_code: it's a sequential identifier within a material group
- Part Number Settings is per-company, providing multi-company account isolation
- Bank number validation differs by payment type (PayNow has different rules than standard transfer)
- Series removal from exports (`remove number when export`) strips internal numbering from external documents
- `auto select series` auto-picks the appropriate series based on transaction context (company, type)
- The system prevents editing of series on certain document types post-creation
