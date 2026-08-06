# UOB Bank Reconciliation & SWIFT

## Summary
UOB bank integration for payment processing including: bank charges moved to deductions in Payment Entry, tax ID and bank account validation, bank account integration with Payment Entry, BIC/SWIFT code standardization, bank purpose codes, payment XML file generation and upload to bank, and automated bank file synchronization.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 8053244fb3 | move bank charges to deductions | 2026-03-04 |
| 1b8b7cc161 | uob: validate tax id and bank account | 2025-11-19 |
| 19df6c8d45 | uob: add bank account to PE | 2025-09-17 |
| fa09f7b763 | add bank account | 2025-09-01 |
| 1b95a50099 | reload update bank details | 2025-07-04 |
| 5b84dafa60 | add bank BIC code standard | 2025-06-12 |
| c3b4f02d2f | add bank purpose | 2025-05-26 |
| 2f8c91e2b7 | send file to bank | 2025-05-07 |
| 1c22c5f502 | add bank fetch on | 2025-05-06 |

## Affected Files
- erpnext/accounts/doctype/payment_entry/payment_entry.json
- erpnext/accounts/doctype/payment_entry_deduction/payment_entry_deduction.json
- erpnext/controllers/uob.py
- erpnext/foms/doctype/payment_approval/payment_approval.json
- erpnext/foms/doctype/uob_file_log/uob_file_log.py
- erpnext/uob/doctype/payment_approval/payment_approval.py
- erpnext/uob/doctype/uob_file_log/uob_file_log.py
- erpnext/setup/utils.py
- erpnext/patches/files/bank_swift.csv
- erpnext/patches/gp/add_bank_standart_sg.py

## Flow/Logic

### 1. Payment XML Generation (`controllers/uob.py: create_payment_xml`)
1. Builds ISO 20022 pain.001.001.03 XML for bank payment instructions.
2. Accepts `invoices` (list of creditor payment details) and `debtor_info` (company/bank details).
3. XML structure:
   - **Group Header**: Message ID, creation datetime, number of transactions, control sum, initiating party BIC.
   - **Payment Information**: Payment method (TRF/CHK), service level code, local instrument (e.g., PAYNOW), category purpose code, requested execution date.
   - **Debtor**: Company name, postal address, organization ID, bank account number, currency, agent BIC.
   - **Credit Transfer Transactions** (per invoice): Payment ID (InstrId/EndToEndId), amount with currency, creditor agent BIC (or proxy type for PayNow), creditor name and address, creditor account, purpose code, remittance info (invoice references), related remittance info (email notification).
4. Supports payment types: bank transfer, cheque (CHK with delivery method), and PayNow (proxy-based).
5. Returns pretty-printed XML string; optionally writes to file.

### 2. File Upload to Bank (`controllers/uob.py: UOBAPI.upload_bank_tx`)
1. Opens the generated XML file.
2. Sends as multipart form POST to `/bank/upload` endpoint on the UOB integration server.
3. Includes destination folder from settings.
4. Returns upload result with status code.

### 3. Bank File Sync & Payment Status (`uob_file_log.py`)
1. **Scheduled sync** (`sync_uob_file`): Downloads new bank response files, creates UOB File Log entries, saves files as attachments.
2. **Payment status parsing** (`_sync_payment_status`):
   - Parses PA213 XML response files (payment status reports).
   - Identifies process stage by filename pattern: `_1` = L1, `R1` = L2, `A1` = L3, `O1001` = L4.
   - Extracts transaction status (ACCP/RJCT), error codes, amounts, BIC, and references.
   - Finds the linked Payment Approval document and calls `update_payment_status(ProcessID, transactions)`.
3. **Payment Entry creation** (`sync_payment_entry`):
   - Parses ES3 CSV bank statement files.
   - Cleans data: strips Excel artifacts from cheque numbers, parses dates from DD/MM/YYYY format.
   - Calculates net amounts per invoice (debit - credit - service charges).
   - Cross-references L4 status to determine accepted vs rejected invoices.
   - Creates Payment Entry documents per supplier:
     - Sets bank account, mode of payment, reference number/date from statement.
     - Adds invoice references with allocated amounts.
     - Adds bank charges as deductions (not separate journal entries).
   - For failed transactions with charges only, creates Journal Entries.
   - Updates Payment Approval status.

### 4. Bank Charges to Deductions
1. Bank service charges (SVC Chg / SERV CHARGE) are added as deduction rows in Payment Entry.
2. Each deduction row includes: charge account (from `default_bank_charge_account`), cost center, amount, description with invoice reference, and a `reff_id` for traceability.
3. The `paid_amount` on Payment Entry includes both invoice amounts and charge amounts.

### 5. BIC/SWIFT Code Standard (`patches/gp/add_bank_standart_sg.py`)
1. A patch imports BIC codes from `patches/files/bank_swift.csv`.
2. Standardizes bank SWIFT/BIC codes for Singapore banks.
3. Used in payment XML generation for creditor agent identification.

### 6. Tax ID & Bank Account Validation
1. During payment processing, validates that suppliers have valid tax IDs and bank accounts.
2. Ensures bank account numbers are present and properly formatted before generating payment files.

### 7. Country Code Resolution (`get_country_code`)
1. Uses `iso3166` package to convert country names to alpha-2 codes.
2. Falls back to frappe Country doctype if iso3166 lookup fails.
3. Used in XML address elements.

## Dependencies
- UOB Integration Settings doctype (host, credentials, folder paths, sync dates)
- Payment Approval doctype (batch management, invoice grouping)
- Payment Entry / Payment Entry Deduction doctypes
- UOB File Log doctype
- Bank / Bank Account doctypes
- `xmltodict` package (XML parsing)
- `xml.etree.ElementTree` (XML generation)
- `iso3166` package (country codes)
- `pandas` (CSV statement parsing)

## Notes
- Payment XML follows ISO 20022 pain.001.001.03 standard required by UOB Singapore.
- PayNow payments use proxy type (e.g., mobile/UEN) instead of BIC for creditor agent.
- The L1-L4 process stages represent progressive bank acknowledgment levels.
- Bank sync skips weekends (Saturday/Sunday).
- `convert_inv_no` handles PAY reference format conversion (e.g., PAY260045A -> PAY-260045).
- Net amount calculation accounts for returned transactions (credits) and distributes charges proportionally across invoices.
- Payment Entry naming follows the pattern: `{PAY-XXXXXX}` with incremental suffixes for multiple entries per approval.
