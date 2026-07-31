# Stock/Account Reposting Error Handling

## Summary
Enhanced error handling for stock reposting: email notifications on repost failures sent to configured support email, repost settings fixes for timeslot configuration, and payment ledger reposting support.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 2fc72bcdb0 | send error reposting to email support | 2026-06-25 |
| 5e0add82cc | fix reposting error | 2026-06-24 |
| 91cf2619de | fix repost settings | 2025-12-15 |
| 1e21bd4584 | fix repost settings | 2025-12-15 |
| de59b50407 | feat: Repost Payment Ledger entries for vouchers | 2022-10-19 |

## Affected Files
- erpnext/stock/doctype/repost_item_valuation/repost_item_valuation.py
- erpnext/accounts/utils.py
- erpnext/stock/__init__.py
- erpnext/accounts/doctype/repost_payment_ledger/

## Flow/Logic
1. **Repost Execution** (`repost_item_valuation.py` → `repost(doc)`):
   - Called by `repost_entries()` which runs hourly via hooks.
   - Processes queued "Repost Item Valuation" documents in order of posting_date/time.
   - On success: sets status to "Completed".
   - On failure: rolls back DB, logs error, stores traceback in `error_log` field.

2. **Error Email Notification** (`notify_error_to_stock_managers`):
   - Triggered when repost fails with a non-recoverable error.
   - **Recipients**: Reads from `frappe.local.conf.email_support` (site config, JSON array of emails). If not configured, silently returns.
   - **Subject**: "Error while reposting item valuation".
   - **Message**: Includes link to the failed Repost Item Valuation document and instructions to check the error and restart reposting.
   - Uses `frappe.sendmail()` for delivery.

3. **Timeslot Configuration** (`in_configured_timeslot`):
   - Reads "Stock Reposting Settings" to determine if reposting is allowed at current time.
   - If `limit_reposting_timeslot` is disabled, always allows reposting.
   - Respects `limits_dont_apply_on` (weekday exemption).
   - Handles both same-day and overnight time ranges (start_time < end_time vs start_time > end_time).

4. **Repost SL Entries** (`repost_sl_entries`):
   - Two modes: "Transaction" (repost by voucher_type/voucher_no) or item/warehouse based.
   - Calls `repost_future_sle()` with appropriate arguments.

5. **Repost GL Entries** (`repost_gl_entries`):
   - Only runs if perpetual inventory is enabled for the company.
   - Gets directly dependent vouchers and affected transactions.
   - Calls `repost_gle_for_stock_vouchers()` for all affected documents.

6. **Dependent Voucher Discovery** (`_get_directly_dependent_vouchers`):
   - Finds all items/warehouses affected by the repost document.
   - Uses `get_future_stock_vouchers()` to find all stock vouchers after the posting date that touch the same items/warehouses.

7. **Payment Ledger Reposting** (`repost_payment_ledger/`):
   - Separate doctype for reposting Payment Ledger entries for specific vouchers.
   - Handles cases where payment ledger gets out of sync with GL entries.

## Dependencies
- Stock Reposting Settings (timeslot configuration)
- Site configuration (`email_support` in common_site_config or site_config)
- Perpetual inventory settings (Company)
- GL Entry and Stock Ledger Entry tables
- Payment Ledger Entry table

## Notes
- Email notifications only fire for non-recoverable errors (not `RecoverableErrors` like deadlocks/timeouts which will be retried).
- The `email_support` config key must be a JSON array of email addresses in site_config.json.
- Repost entries are processed in posting_date/time order to maintain data consistency.
- The fix commits (91cf2619de, 1e21bd4584) addressed issues in `accounts/utils.py` and `stock/__init__.py` related to timeslot checking and repost trigger conditions.
- In tests (`frappe.flags.in_test`), repost errors are raised immediately rather than caught silently.
