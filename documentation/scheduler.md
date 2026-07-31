# Scheduler & Background Jobs

## Summary
Custom scheduled tasks registered in hooks.py for automated operations including: FOMS data sync (suppliers, customers, sales orders, raw materials, products, recipes, packaging, stock receipts), UOB bank file download and payment matching, currency exchange rate fetching, stock reorder, email reminders, and backup operations.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 57ffabd9ba | add scheduler 10 minutes | 2025-06-26 |
| 5d229648e7 | add to scheduler | 2025-02-25 |
| 1ac47563b2 | increase time scheduler | 2025-02-12 |
| 8559ba7a99 | add to scheduler | 2025-01-30 |
| c35d174d36 | add to scheduler | 2025-01-14 |
| a6670e2c84 | add to scheduler | 2024-12-18 |
| a0995e2e32 | add to scheduler | 2024-12-18 |
| b83e5c1411 | get recipe manual and scheduler | 2024-01-30 |
| 019567836a | add to scheduler | 2024-01-29 |
| 538465606b | create scheduler fetch rate | 2023-11-02 |

## Affected Files
**Hooks Configuration**
- erpnext/hooks.py (scheduler_events section)

**FOMS Integration**
- erpnext/controllers/foms.py (update_stock_receipt, update_foms_supplier, update_foms_customer, update_foms_sales_order, get_raw_material, get_products, get_recipe, get_packaging)
- erpnext/foms/doctype/foms_integration_settings/foms_integration_settings.py

**UOB Bank Integration**
- erpnext/controllers/uob.py (sync_uob_file)
- erpnext/foms/doctype/uob_file_log/uob_file_log.json

**Currency Exchange**
- erpnext/setup/doctype/currency_exchange/currency_exchange.py (fetch_month_rate)
- erpnext/setup/utils.py (get_exchange_rate)

## Flow/Logic

### Scheduler Events (hooks.py)

#### Cron Jobs (specific intervals)
| Schedule | Function | Purpose |
|----------|----------|---------|
| `*/5 * * * *` | `erp_api.run_pending_harvesting_transfer` | Process pending harvesting transfers every 5 min |
| `*/5 * * * *` | `erp_api.run_pending_harvesting` | Process pending harvesting every 5 min |
| `*/5 * * * *` | `erp.read_email_inbox` | Read incoming emails every 5 min |
| `*/30 * * * *` | `uob.sync_uob_file` | Download and process UOB bank files every 30 min |
| `0/30 * * * *` | `video.update_youtube_data` | Update YouTube video data every 30 min |
| `30 * * * *` | `gl_entry.rename_gle_sle_docs` | Rename GL/SLE docs hourly at :30 |
| `45 0 * * *` | `reorder_item.reorder_item` | Auto reorder items daily at 00:45 |
| `0 5 * * *` | `minio_backup_settings.upload_backup` | Minio backup at 5:00 AM |
| `40 20 * * *` | `minio_backup_settings.upload_backup2` | Second backup at 8:40 PM |
| `0 23 * * *` | `accounts.utils.auto_create_exchange_rate_revaluation_last_day` | Exchange rate revaluation at 11 PM |
| `0 6 * * *` | `erp.reminder_submit_invoice` | Remind to submit invoices at 6 AM |
| `0 6 * * *` | `erp.reminder_submit_purchase_invoice` | Remind to submit purchase invoices at 6 AM |
| `0 */4 * * *` | `erp.read_email_inbox` | Read email inbox every 4 hours |

#### Hourly
| Function | Purpose |
|----------|---------|
| `foms.update_stock_receipt` | Sync Purchase Receipt stock data to FOMS |

#### Daily
| Function | Purpose |
|----------|---------|
| `currency_exchange.fetch_month_rate` | Fetch monthly exchange rates for all currency pairs |
| `foms.update_foms_supplier` | Sync supplier data to FOMS |
| `foms.update_foms_customer` | Sync customer data to FOMS |
| `foms.update_foms_sales_order` | Sync sales orders to FOMS |
| `foms.get_raw_material` | Pull raw materials from FOMS |
| `foms.get_products` | Pull products from FOMS |
| `foms.get_recipe` | Pull recipes from FOMS |
| `foms.get_packaging` | Pull packaging data from FOMS |
| `scrap_request.collect_expired_items` | Collect expired items for scrap |
| `scrap_request.collect_expired_product` | Collect expired products for scrap |
| `email_invoice.pull_erp_po` | Pull PO data for email invoice AI agent |

#### Monthly
| Function | Purpose |
|----------|---------|
| `depreciation.post_depreciation_entries` | Post asset depreciation entries |
| `erp.trial_balance_different_issue` | Check trial balance discrepancies |

### UOB Bank File Sync (`sync_uob_file`)
1. Checks if sync is disabled via `stop_sync_file` setting.
2. Skips weekends (Saturday/Sunday).
3. Gets the last download date from UOB Integration Settings.
4. Calls `download_bank_tx_bulk` to fetch files newer than last download.
5. For each file returned:
   - Creates a `UOB File Log` document.
   - Decodes base64 content to XML.
   - Saves as a private file under "Home/Bank" folder.
   - Calls `sync_payment_status` to match bank transactions with ERP payments.
6. Updates `last_sync_date` and `last_file_name` on settings.

### FOMS Stock Receipt Sync (`update_stock_receipt`)
1. Triggered via `sync_controller` which processes pending Sync Log entries for "Purchase Receipt".
2. For each Purchase Receipt item:
   - Skips items in excluded item groups.
   - Gets Stock Ledger Entry info (batch, qty).
   - Looks up FOMS IDs for batch, warehouse, supplier, and raw material.
   - Sends stock receipt data to FOMS API with quantity, batch reference, expiry date, warehouse, and supplier.

### Currency Exchange Rate Fetch (`fetch_month_rate`)
1. Runs daily but only acts on the 1st of each month.
2. Checks if rate already fetched for this month (prevents duplicates).
3. Calls external bank API to verify data availability (skips if holiday/no data).
4. Gets all unique currency pairs ever used in Currency Exchange.
5. Also adds reverse pairs if not already present.
6. For each pair, calls `get_exchange_rate` with `from_scheduler=1` flag to create the exchange rate record.

### FOMS Supplier/Customer Sync
1. Uses `sync_controller` pattern: processes pending Sync Log entries.
2. Gets the document, checks if it belongs to a FOMS-enabled company.
3. Sends create/update/delete requests to FOMS API based on document status.

## Dependencies
- Frappe Scheduler framework (hooks.py scheduler_events)
- Sync Log doctype (frappe.core.doctype.sync_log) for pending operation queue
- FOMS Integration Settings (API credentials, farm_id, enable flag)
- UOB Integration Settings (host, credentials, stop_sync_file, last_download_date)
- External APIs: FOMS farm management system, UOB bank API, currency exchange API

## Notes
- The `*/5 * * * *` cron for `read_email_inbox` overlaps with the `0 */4 * * *` entry for the same function, providing both frequent and guaranteed execution.
- UOB sync skips weekends since banks don't process files on Saturday/Sunday.
- FOMS sync uses a Sync Log queue pattern: documents are queued on save/submit/cancel, and the scheduler processes them in order. This decouples user actions from API calls.
- The `ITEM_GROUP_NOT_SYNC` list in foms.py excludes certain item groups from being synced to FOMS.
- `fetch_month_rate` has a guard against holidays: if the bank API returns no `bank_date`, it defers to the next day.
- Minio backup runs twice daily (5:00 AM and 8:40 PM) for redundancy.
