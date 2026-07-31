# AI Email Invoice

## Summary
Automated Purchase Invoice creation from incoming emails using Google Vision OCR for text extraction and an AI agent for structured data parsing. Includes supplier matching via domain/name fuzzy lookup, AI Agent Memory for learning from corrections, a refinement step using historical patterns, and support for multi-page PDFs.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 950a3a76be | fix(email_invoice): fallback to memory for tax template when extraction data missing | 2026-07-03 |
| 392b3cc771 | fix(email_invoice): strengthen refinement prompt to always include tax_template | 2026-07-03 |
| 822d2d9460 | feat(email_invoice): add refinement step with memory context for better extraction | 2026-06-26 |
| 549f55f6b6 | fix(email_invoice): improve prompt and fallback for supplier extraction | 2026-06-25 |
| a50c20d1bb | feat(email_invoice): integrate AI Agent Memory for supplier matching | 2026-06-24 |
| 1ed79a7cc3 | feat(ai_agent_memory): add AI Agent Memory doctype for learning from corrections | 2026-06-24 |
| 26ae3e25a6 | fix(email_invoice): handle missing supplier gracefully | 2026-06-23 |
| 90c98c11c2 | feat(email_invoice): add multi-page PDF support and improve line item extraction | 2026-06-20 |
| 80ae413ba3 | fix(email_invoice): handle rate/amount extraction edge cases | 2026-06-19 |
| dec7cb25ca | feat(email_invoice): improve OCR extraction with structured prompts | 2026-06-18 |
| bf97e2b200 | feat(email_invoice): initial implementation with Google Vision OCR | 2026-06-17 |

## Affected Files
- erpnext/ai_agent/__init__.py
- erpnext/ai_agent/doctype/__init__.py
- erpnext/ai_agent/doctype/ai_agent_settings/ai_invoice_converter.py
- erpnext/ai_agent/doctype/email_invoice/__init__.py
- erpnext/ai_agent/doctype/email_invoice/email_invoice.js
- erpnext/ai_agent/doctype/email_invoice/email_invoice.json
- erpnext/ai_agent/doctype/email_invoice/email_invoice.py
- erpnext/ai_agent/doctype/email_invoice/test_email_invoice.py
- erpnext/controllers/google_vision.py
- erpnext/gp_erp/doctype/ai_agent_memory/__init__.py
- erpnext/gp_erp/doctype/ai_agent_memory/ai_agent_memory.js
- erpnext/gp_erp/doctype/ai_agent_memory/ai_agent_memory.json
- erpnext/gp_erp/doctype/ai_agent_memory/ai_agent_memory.py
- erpnext/gp_erp/doctype/ai_agent_memory/test_ai_agent_memory.py
- erpnext/modules.txt

## Flow/Logic

### 1. Email Receipt & Processing (`email_invoice.py: process_email`)
1. A Communication (email) is received and linked to an Email Invoice document.
2. `sync_email` copies sender, date, subject, and message body (truncated if too long).
3. `process_email` is called:
   - Collects file attachments from the Email Invoice or linked Communication.
   - If no attachments: records reason "no_attachment" and exits.
   - Initializes `AIAgentClient` from AI Agent Settings.
   - For each attachment:
     - Verifies file exists on disk (tries alternative with same content hash if missing).
     - Copies attachment to Email Invoice for traceability.
     - Rejects non-PDF files with reason "not_pdf".
     - Attempts PDF-to-image conversion to detect encrypted/invalid PDFs.
     - Calls `agent.extract_invoice(path, references, email)` for end-to-end extraction.
     - Enhances payload (supplier matching, PO normalization).
     - Refines with memory (second-layer validation).
     - Creates Purchase Invoice from extracted data.
   - Stores extracted JSON in `data_result` field.
   - Sets status: "Matched" (PI created), "Pending" (PO found), or "Unknown" (failed).

### 2. OCR Text Extraction (`ai_invoice_converter.py` + `google_vision.py`)
1. `AIAgentClient.extract_text` delegates to `extract_text_via_google_vision`.
2. `google_vision.py: extarct_text_from_file`:
   - For images: calls Google Vision `document_text_detection` API directly.
   - For PDFs: uses PyMuPDF (fitz) to render each page to PNG, then sends each page image to Google Vision API.
   - Concatenates text from all pages.
   - Requires `google_cloud_vision_key` in site config.
3. Appends sender email domain(s) to extracted text for supplier identification context.

### 3. Document Classification (`ai_invoice_converter.py: validate_text`)
1. Before extraction, the text is classified using `chat_completion` with a system prompt.
2. The AI determines if the document's primary purpose is requesting payment (invoice) vs other document types.
3. Returns `true` (is invoice) or `false` (not invoice).
4. If classification fails, defaults to treating as invoice (optimistic fallback).

### 4. Structured Data Extraction (`ai_invoice_converter.py: get_invoice_data`)
1. Sends OCR text (first 2000 chars) and supplier default to the AI server at `/get-invoice-data`.
2. AI server returns structured JSON with: document info, supplier, currency, items, summary, payment details.

### 5. Supplier Matching (`ai_invoice_converter.py: enhance_payload`)
1. First attempts to match supplier by website/email domain in Supplier doctype.
2. If supplier not found in ERPNext:
   - Calls `AIAgentClient.get_supplier` with supplier names, domains, and reference data.
   - Uses fuzzy matching with configurable threshold from Buying Settings (`supplier_threshold`).
   - Updates the payload with matched supplier code.
3. PO number is normalized: corrects OCR misreads (O->0, I->1, etc.), ensures PO format `PO######/YYYY`.

### 6. Memory Refinement (`email_invoice.py: refine_with_memory`)
1. After initial extraction, fetches AI Agent Memory for the identified supplier.
2. If memory exists, calls `chat_completion` with a refinement prompt that:
   - Fixes item names using historical "Scanned Name -> Item Name" mappings.
   - Pre-fills Cost Center and Expense Head from memory.
   - Validates rates against historical averages (flags >20% deviation).
   - Ensures `tax_template` is always present in summary (from memory if missing).
3. Returns refined JSON in same structure; falls back to original on failure.

### 7. Purchase Invoice Creation

#### From Purchase Order (`create_invoice`)
1. Detects PO reference from extracted data.
2. Builds PI via `make_purchase_invoice(PO)`.
3. Sets naming series `TEMP-PI.#####./.YYYY`, bill_no, bill_date, currency.
4. Matches buying price list to invoice currency.
5. Updates item rates from extracted data (maps by item_code or index).
6. Sets historical cost center and expense account from latest submitted PI for same supplier.
7. Applies tax template: extraction data > memory > company default.
8. Saves with `ignore_mandatory`, `ignore_permissions`, `ignore_links` flags.
9. Attaches bank account info as Comment on PI.
10. Records rate changes as Comment.

#### Non-stock PI (`create_purchase_invoice_non_stock`)
1. Creates a new PI with `non_stock_item=1`.
2. All items use generic "Non-stock" item code with extracted item names/descriptions.
3. Validates: supplier exists, currency exists, UOM exists.
4. Missing links (Supplier, Currency, UOM) recorded as Comment on PI for manual review.
5. Rejects if multiple currencies detected across line items.
6. Same tax template and historical data logic as PO-based creation.
7. Duplicate prevention: checks for existing PI with same `bill_no` + `bill_date`.

### 8. AI Agent Memory (`ai_agent_memory.py`)

#### Data Model
- `reff_doctype`: Reference type ("Supplier" or "Customer")
- `reff_name`: Entity name
- `company`: Company name
- `memory`: Markdown content with structured supplier patterns
- `updated_at`: Last update timestamp

#### Memory Content Structure (Markdown)
```
# Supplier Name
## Items
| Scanned Name | Item Name | UOM | Cost Center | Expense Head | Avg Rate |
## Invoice Pattern
- Currency, Payment Terms
## Addresses
- Shipping, Billing
## Tax & Accounts
- Tax Template, tax details
```

#### Lifecycle
1. `update_memory_on_submit`: Hooked to Purchase Invoice `on_submit` event.
2. `update_memory_from_pi(pi_name)`: Regenerates memory from a submitted PI.
3. `_get_scanned_names`: Fetches original OCR-scanned item names from the linked Email Invoice's `data_result` JSON.
4. `_generate_memory_from_pi`: Builds markdown memory combining scanned names with actual item mappings, cost centers, expense accounts, rates, addresses, and tax templates.
5. Memory is upserted (update if exists, create if not) per supplier+company.

#### Usage in Processing
- `get_memory(ref_doctype, ref_name, company)`: Retrieves memory content for use in refinement prompts and tax template fallback.

### 9. Post-Creation Processing
1. Temporary PI naming (`TEMP-PI.#####./.YYYY`) is renamed to final series (`PI.#####./.YYYY`) on submit via `change_temporary_invoice`.
2. Bank account data extracted from invoices is stored as Info Comments and can be converted to Bank Number records via `convert_bank_data`.
3. Communication is linked to the created PI (`reference_doctype`/`reference_name`).

### 10. Error Handling & Reason Tracking
1. Categorized reason system tracks failures: attachment, pdf, agent, pi, system.
2. Short reason codes for list filtering: "System Error", "PI Missing Data", "PI Unknown Item", "PDF Encrypted", "Not PDF", "Agent No Result", etc.
3. Full reason details stored as JSON in `error_trace` field.

## Dependencies
- AI Agent Settings doctype (`server_url` for AI extraction server)
- Google Cloud Vision API (`google_cloud_vision_key` in site config)
- AI Agent Memory doctype
- Purchase Order / Purchase Invoice doctypes
- Communication doctype (email handling)
- `erpnext.controllers.ai.chat_completion` (LLM calls for validation/refinement)
- PyMuPDF (`fitz`) for PDF rendering
- `email_reply_parser` / `BeautifulSoup` for email content parsing

## Notes
- OCR text is truncated to 2000 characters before sending to AI server for invoice data extraction.
- Duplicate invoice prevention uses `bill_no` + `bill_date` combination.
- Memory errors are logged but never block PI creation or submission.
- The supplier threshold for fuzzy matching is configurable in Buying Settings.
- Sender domain extraction excludes the company's own email domains (configured in site config `email_whitelist`).
- Tax template resolution priority: extracted data > memory lookup > company default GST template.
- The system handles encrypted PDFs gracefully by detecting `doc.needs_pass` and recording an appropriate reason.
