# Payment

## Summary
Payment entry customizations, UOB bank payment integration (XML generation, API communication, status tracking), Payment Approval workflow with multi-level authorization, bulk payment approval page, PayNow support, automatic Payment Entry creation from bank statements, and Payment Ledger report.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 3b809feb78 | remove default costs enter on make payment | 2026-06-25 |
| 0ad9f19853 | fix total payment approval | 2026-06-12 |
| 41e2aca834 | fixing payment #4 | 2026-05-21 |
| 7e2c74c7c9 | fix payment version #3 | 2026-05-21 |
| e2d831ca92 | fix payment version failed | 2026-05-21 |
| 54fc0db2d0 | fix payment version v2 | 2026-05-21 |
| 04bb12e497 | fix payment version | 2026-05-21 |
| db5678ef2f | fixing payment made from bank statement | 2026-04-07 |
| 0041499da3 | add mode of payment: paynow | 2026-02-27 |
| 224c6fae64 | fix payment entry name bug | 2026-02-27 |
| 4b84b2aa96 | fix payment entry reference | 2026-02-24 |
| 38ed3f6583 | uob: add name flag number for duplicate payment entry | 2025-11-24 |
| 0537b70429 | uob: add print format payment approval | 2025-09-18 |
| ac03cba16b | uob: change text pending to payment | 2025-09-16 |
| 3b221cdb7c | update payment approval status | 2025-09-15 |
| b34babaf83 | uob: fixing bulk payment statement | 2025-09-15 |
| e23491fb32 | add bank charges and mapping payment entry | 2025-09-11 |
| f9b278126f | uob: decoding payment result | 2025-09-10 |
| 6684dbc3ea | add payment keyword | 2025-08-15 |
| a75c9a24b5 | create payment entry from bank statement | 2025-07-03 |
| ... and 34 more commits |

## Affected Files
**Payment Entry Core**
- erpnext/accounts/doctype/payment_entry/payment_entry.py
- erpnext/accounts/doctype/payment_entry/payment_entry.json
- erpnext/accounts/doctype/payment_entry_reference/payment_entry_reference.json

**Payment Approval (UOB)**
- erpnext/uob/doctype/payment_approval/payment_approval.py
- erpnext/uob/doctype/payment_approval/payment_approval.js
- erpnext/uob/doctype/payment_approval/payment_approval.json

**Bulk Approval Page**
- erpnext/uob/page/payment_bulk_approval/payment_bulk_approval.js

**UOB Integration**
- erpnext/controllers/uob.py
- erpnext/uob/doctype/uob_file_log/uob_file_log.py
- erpnext/uob/doctype/uob_file_log/uob_file_log.json
- erpnext/uob/print_format/payment_approval/payment_approval.json

**Payment Ledger Report**
- erpnext/accounts/report/payment_ledger/payment_ledger.py
- erpnext/accounts/report/payment_ledger/payment_ledger.js
- erpnext/accounts/report/payment_ledger/payment_ledger.json

**Payment Invoice List (child table)**
- erpnext/foms/doctype/payment_invoice_list/payment_invoice_list.py
- erpnext/foms/doctype/payment_invoice_list/payment_invoice_list.json

**Other**
- erpnext/accounts/doctype/journal_entry/journal_entry.py
- erpnext/accounts/doctype/mode_of_payment/mode_of_payment.js
- erpnext/accounts/doctype/mode_of_payment/mode_of_payment.json
- erpnext/accounts/doctype/bank/bank.json
- erpnext/accounts/doctype/bank_number/bank_number.json
- erpnext/accounts/party.py
- erpnext/controllers/accounts_controller.py
- erpnext/controllers/erp.py
- erpnext/controllers/taxes_and_totals.py
- erpnext/loan_management/doctype/loan/loan.py
- erpnext/loan_management/doctype/loan_repayment/loan_repayment.py
- erpnext/setup/doctype/company/company.json
- erpnext/utilities/bulk_transaction.py

## Flow/Logic

### Payment Entry Validation
1. `PaymentEntry.validate()` sets up party account field (paid_from for Receive, paid_to for Pay).
2. Validates payment type, party details, exchange rate, mandatory fields.
3. Validates reference documents, sets tax withholding, calculates amounts.
4. `validate_paid_invoices()` ensures invoices are not already fully paid.
5. `validate_allocated_amount()` checks allocation doesn't exceed outstanding.
6. On submit: creates GL entries, updates outstanding amounts, updates advance paid.

### UOB Payment Approval Workflow
1. User creates a Payment Approval document, selects supplier and invoices to pay.
2. `PaymentApproval.validate()` runs:
   - `set_status()` — sets initial status to "Draft"
   - `set_requested_by()` — captures the requesting user
   - `validate_paynow()` — ensures proxy numbers exist for PayNow transfers
   - `validate_reqd_data()` — checks required fields
   - `validate_select()` — ensures at least 1 invoice is selected
   - `validate_payment()` — determines payment method/type (TRF/CHQ) and UOB codes (URGP, URNS, NURG, BOOK)
   - `validate_bank_number()` — validates bank account digits (HSBC/OCBC/SBI require 10+ digits)
   - `validate_invoice()` — validates invoice data
   - `calculate_amount()` — totals selected invoices
   - `process_xml_file()` — generates XML payment file for UOB
   - `set_batch_number()` — extracts batch number from document name

3. On submit: updates approval date/time, removes unselected rows.

### UOB API Integration (`controllers/uob.py`)
1. `UOBAPI` class handles HTTP communication with UOB bank API.
2. Uses session with retry adapter (max 3 retries).
3. `create_payment_xml()` generates the XML file for batch payments.
4. Payment methods mapped to UOB codes:
   - TT/MEPS/IAFT → URGP (urgent payment)
   - PayNow → URNS with PAYNOW property
   - FAST → URNS
   - IBG → NURG (non-urgent)
   - IBG Express → BOOK

### Payment Status Tracking
1. `update_payment_status()` receives process_id and transaction results from UOB.
2. Status progression: Draft → Pending → Approved → Received (process_id=1) → In Progress (process_id=3) → Complete/Failed (process_id=4).
3. Transaction results: ACCP=Success, RCVD/ACTC=In Progress, others=Failed.
4. For successful payments, amount matching uses tolerance of $1.
5. Status changes are logged as Workflow comments.

### Automatic Payment Entry from Bank Statement
1. Bank statement entries are matched to outstanding invoices.
2. `create_payment_entry()` uses `get_payment_entry()` to create PE from Purchase Invoice.
3. Sets bank account, mode of payment (Bank Draft), reference number, and reference date.
4. Auto-generated PE is marked with `auto_generated=1`, inserted and submitted.

### Bulk Payment Approval Page
1. Custom page at `/payment-bulk-approval` with responsive design.
2. Lists Payment Approval documents with filters (status, date, supplier).
3. Supports inline approval actions with expandable detail rows.
4. Mobile-responsive with collapsible filters and stacked layout.

### Payment Cancellation Guard
1. `on_cancel()` prevents cancellation if status is Approved, Received, In Progress, or Complete.
2. This ensures payments already sent to UOB cannot be reversed from ERPNext side.

## Dependencies
- UOB Integration Settings (single doctype for API configuration)
- Bank Number doctype (stores bank account details, proxy numbers)
- Purchase Invoice (source for payment references)
- Payment Ledger Entry (frappe core for tracking)
- Bank Account doctype (for company bank details)
- Mode of Payment (extended with PayNow)

## Notes
- Payment method "PayNow" requires a proxy_number on the supplier's bank number record.
- HSBC/OCBC/SBI bank accounts require minimum 10-digit account numbers (validated in `validate_bank_number`).
- The `process_id` field tracks UOB's multi-level approval stages (1-4). Updates only apply if new process_id >= current.
- Duplicate payment entry names are handled by adding a flag number suffix (`38ed3f6583`).
- Payment version fixes (multiple commits on 2026-05-21) indicate iterative fixes to XML generation format.
- The bulk approval page uses infinite scroll with a "Load More" pattern rather than traditional pagination.
- `on_cancel` check is strict — once UOB has received the payment file, it cannot be cancelled in ERPNext.
