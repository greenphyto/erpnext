# Asset Disposal Entry

## Summary
Custom disposal date support for asset scrapping, option to save disposal journal entry as draft (instead of auto-submit), and warning validation for unposted depreciation entries before disposal.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 8e8ef37f22 | custom disposal date | 2026-07-14 |
| d36a39871f | add save submit/draft disposal entry | 2026-07-14 |
| 9568885463 | warn posting rest entry disposal | 2026-07-14 |

## Affected Files
- erpnext/assets/doctype/asset/asset.js
- erpnext/assets/doctype/asset/depreciation.py
- erpnext/accounts/doctype/journal_entry/journal_entry.py
- erpnext/accounts/doctype/sales_invoice/sales_invoice.py
- erpnext/assets/doctype/asset_capitalization/asset_capitalization.py

## Flow/Logic
1. **Custom Disposal Date**: `scrap_asset(asset_name, disposal_date=None, submit_jv=True)` in `depreciation.py` accepts an optional `disposal_date` parameter. If not provided, defaults to today. The disposal date is used for the journal entry posting date and stored on the Asset.

2. **Future Depreciation Block**: Before scrapping, `check_future_posted_depreciation(asset, disposal_date)` checks for any already-posted depreciation journal entries after the disposal date. If found, it throws an error requiring those entries to be cancelled first.

3. **Depreciate Up To Disposal**: `depreciate_asset(asset, disposal_date)` calls `prepare_depreciation_data(date_of_disposal=date)` and then `make_depreciation_entry()` to post any pending depreciation up to the disposal date.

4. **Unposted Depreciation Warning**: `_warn_unposted_depreciation(asset, disposal_date)` warns the user if there are unposted depreciation schedule entries on or before the disposal date.

5. **Draft/Submit JV Option**: The `submit_jv` parameter (default True) controls whether the disposal Journal Entry is submitted or saved as draft:
   - `submit_jv=1`: JE is submitted immediately (original behavior).
   - `submit_jv=0`: JE is saved as draft, allowing review before submission.

6. **Pre-disposal Check (Sales Invoice path)**: `check_unposted_depr_before_disposal(asset_name, disposal_date)` is called from `asset.js` before creating a Sales Invoice for asset sale. It returns the count of unposted depreciation entries and shows a confirmation dialog to the user.

7. **GL Entries**: `get_gl_entries_on_asset_disposal()` computes accumulated depreciation amount based on the disposal date (from schedule entries), then creates credit/debit entries for fixed asset account, accumulated depreciation account, and profit/loss on disposal.

8. **Asset Status**: After JE creation, the asset's `disposal_date` and `journal_entry_for_scrap` fields are updated, and status is set to "Scrapped".

## Dependencies
- Asset depreciation schedule
- Journal Entry doctype
- Company depreciation settings (series, accounts)
- Asset Category Account configuration

## Notes
- The `disposal_date` must not have future posted depreciation entries; otherwise the operation is blocked.
- When selling via Sales Invoice, the JS shows a confirm dialog with the count of unposted entries.
- Restoring a scrapped asset cancels (or deletes if draft) the scrap JE and resets the depreciation schedule.
