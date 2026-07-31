# Asset & Depreciation

## Summary
Custom asset depreciation logic for GP ERPNext including grouped monthly depreciation entries, skip month handling, asset code mapping with QR codes, asset creation from stock entries, and depreciation schedule adjustments. Replaces standard per-asset depreciation with a combined journal entry approach grouped by month, company, and finance book.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 88a1f630b4 | Revert "selected skip depreciation asset" | 2025-07-07 |
| 05c1ad6919 | selected skip depreciation asset | 2025-06-30 |
| 2d6b2c9f25 | add disable reason asset | 2025-06-10 |
| 640fb9f9a9 | fix non list asset name | 2025-06-10 |
| 158544ff07 | add button asset (temp) | 2024-12-02 |
| b50afe1d14 | fix report asset depreciation | 2024-11-28 |
| 36f7329ada | linked asset depreciation | 2024-11-26 |
| 9a0da1ebe8 | disable purchase on stock entry asset | 2024-10-08 |
| f58a25d657 | store asset creation | 2024-10-08 |
| 474e63133e | fix item asset | 2024-10-08 |
| 1dfc984496 | create asset | 2024-10-02 |
| b526d3f658 | add asset item for stock entry | 2024-10-02 |
| 366f096344 | validate asset category | 2024-10-02 |
| d796fbdb6e | set asset code data | 2024-10-02 |
| 4beb65ac4b | add filter to asset code | 2024-10-02 |
| 4b769a027e | no copy asset data | 2024-07-17 |
| 8765d2ff1a | fix asset new | 2024-06-26 |
| 9a2b80ca13 | asset calculation adjust | 2024-06-24 |
| 7b6e551740 | add group depreciation | 2024-06-20 |
| dfb56e5ec5 | make group depreciation every month | 2023-09-29 |

## Affected Files
**Core Asset Logic**
- erpnext/assets/doctype/asset/asset.py
- erpnext/assets/doctype/asset/asset.js
- erpnext/assets/doctype/asset/asset.json
- erpnext/assets/doctype/asset/asset_list.js
- erpnext/assets/doctype/asset/depreciation.py
- erpnext/assets/doctype/asset/test_asset.py

**Asset Utilities & Code Map**
- erpnext/assets/utils.py (QR code generation)
- erpnext/assets/doctype/asset_code_map/asset_code_map.json
- erpnext/assets/doctype/depreciation_schedule/depreciation_schedule.json

**Reports**
- erpnext/accounts/report/asset_depreciations_and_balances/asset_depreciations_and_balances.py
- erpnext/accounts/report/asset_depreciations_and_balances/asset_depreciations_and_balances.js
- erpnext/accounts/report/asset_depreciations_and_balances/report_new.py

**Stock Entry Integration**
- erpnext/stock/doctype/stock_entry/stock_entry.js
- erpnext/stock/doctype/stock_entry/stock_entry.py
- erpnext/stock/doctype/stock_entry_detail/stock_entry_detail.json
- erpnext/stock/doctype/item/item.js
- erpnext/stock/doctype/item/item.json
- erpnext/stock/doctype/item/item.py

**Journal Entry & Accounts**
- erpnext/accounts/doctype/journal_entry/journal_entry.js
- erpnext/accounts/doctype/journal_entry/journal_entry.py
- erpnext/accounts/report/cash_flow/cash_flow.py

**Patches**
- erpnext/patches/v14_0/repair_grrenphyto_asset.py
- erpnext/patches/v14_0/update_expense_account.py

**QR Code**
- erpnext/www/qrcode_preview.html
- erpnext/www/qrcode_preview.py

## Flow/Logic

### Grouped Monthly Depreciation (Core Custom Logic)
1. `post_depreciation_entries(date, commit, asset_category)` is the main scheduler entry point.
2. Checks if automatic depreciation booking is enabled in Accounts Settings.
3. Uses `get_last_day(add_months(date, -1))` to determine the depreciation period (previous month-end).
4. `get_depreciable_assets(date, asset_category)` queries assets with pending depreciation schedules matching the month/year using `DATE_FORMAT(ds.schedule_date, "%%m %%Y")`.
5. Groups assets by key: (schedule_date_last_day, company, finance_book, asset_category).
6. For each group, calls `make_depreciation_entry(assets_list, date)` to create ONE combined Journal Entry.
7. The combined JE contains credit/debit rows for each asset's depreciation amount, all in a single document.

### make_depreciation_entry (Combined JE)
1. Accepts a list of asset names and a date.
2. Iterates assets, finds matching schedule rows for the given month/year.
3. Gets depreciation accounts (fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account).
4. Creates a single Journal Entry with voucher_type "Depreciation Entry".
5. For each asset's schedule row, appends credit (accumulated depreciation) and debit (depreciation expense) entries.
6. Sets cost centers per account using `erpnext.get_default_cost_center(company, account)`.
7. Saves and submits the JE (if no workflow exists).
8. Links the JE back to each depreciation schedule row via `d.journal_entry`.

### Asset Autoname (Custom Naming with Asset Code Map)
1. On asset creation, `autoname()` checks if the item has an `asset_code` field.
2. Looks up the series pattern from `Asset Code Map` (child table in Accounts Settings).
3. Uses `parse_naming_series()` with the mapped series to generate the asset name.
4. Falls back to standard `naming_series` if no asset code mapping exists.

### QR Code Generation
1. `create_asset_qrcode(self)` in `assets/utils.py` generates a QR code for each asset.
2. Called during asset `validate()`.
3. QR code links to the asset preview page (`/qrcode_preview`).
4. `www/qrcode_preview.html` and `www/qrcode_preview.py` serve the public QR landing page.

### Asset Creation from Stock Entry
1. Stock entries for fixed asset items can trigger automatic asset creation.
2. `stock_entry_detail.json` extended with asset-related fields.
3. Validates asset category exists on the item before creation.
4. `disable purchase on stock entry asset` prevents manual purchase entry when asset is linked.

### Depreciation Schedule Calculation
1. Pro-rata calculation is disabled (`has_pro_rata = False`) - depreciation starts from the configured start date.
2. Schedule dates align to month-ends when start date is last day of month (`should_get_last_day`).
3. `_make_depreciation_schedule()` generates all pending rows based on total_number_of_depreciations minus booked.
4. Expected value after useful life is respected - last period adjusts to hit target value.

### Disposal & Accumulated Depreciation
1. `get_accumulated_depreciation_from_schedule()` computes actual accumulated depreciation from posted schedule rows only.
2. `check_unposted_depreciation_entries()` warns about unposted entries before disposal.
3. `check_future_posted_depreciation()` blocks disposal if entries exist after disposal date.
4. `_sync_accumulated_depreciation_header()` keeps header field in sync with schedule totals.

### Asset Disable/Skip
1. Assets can be disabled with a reason field (`disable_reason`).
2. Disabled assets (disabled=1) are excluded from depreciation queries.
3. "Skip depreciation" feature was added then reverted - certain assets could be temporarily excluded from monthly runs.

## Dependencies
- Accounts Settings (book_asset_depreciation_entry_automatically toggle, asset_code_map child table)
- Company (depreciation_cost_center, disposal_account, series_for_depreciation_entry)
- Asset Category (account mappings per company)
- Item (is_fixed_asset, asset_category, asset_code fields)
- Journal Entry (Depreciation Entry voucher type)
- Company Admin (switch_to_company_admin for scheduled runs)

## Notes
- The grouped depreciation is the key custom feature: standard ERPNext creates one JE per asset per period; GP creates one JE per (month, company, finance_book, asset_category) group.
- `get_month_year(date)` returns format "MM YYYY" for grouping depreciation schedules by period.
- Pro-rata depreciation is intentionally disabled - all assets depreciate from their configured start date without partial-period adjustment.
- The `no_copy` flag on asset data fields prevents asset information from being duplicated when copying stock entries.
- `repair_grrenphyto_asset.py` patch fixes historical asset data inconsistencies.
- Asset code map supports multiple naming series per asset category/account combination.
- Cash flow report (`cash_flow.py` and `cash_flow_greenphyto.py`) was adjusted to correctly handle the grouped depreciation entries.
