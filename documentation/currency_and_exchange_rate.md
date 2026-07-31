# Currency & Exchange Rate

## Summary
Multi-currency handling with automatic exchange rate fetching from MAS (Monetary Authority of Singapore) and Frankfurter APIs, first-day-of-month rate logic, currency exchange record saving, and multi-currency validation across transactions.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 3e32d67f36 | fix currency exchange | 2026-06-02 |
| 206e3fca22 | validate account currency or part number | 2026-05-19 |
| 80a1481c71 | validate account currency or part number | 2026-05-19 |
| bca34ffb97 | fetch currency from account | 2026-04-13 |
| d5ecf1faa0 | uob: reqd for currency | 2025-11-18 |
| 2fdf76b723 | uob: validate different payee currency | 2025-11-12 |
| 323ac3a436 | uob: fixing show currency default | 2025-11-12 |
| 0687a9af67 | prod: fix currency exchange | 2025-09-29 |
| 634c2636b5 | validate different currency and fix status | 2025-09-11 |
| 45501791b4 | add filter currency | 2025-09-08 |
| aa314aa6ed | format currency and filter currency | 2025-08-25 |
| 33dd1e0018 | add GST and valdiate multi currency | 2025-07-18 |
| ee23022b74 | add currency and fix issue | 2025-07-04 |
| 0bdeee283a | fetch currency every first month | 2025-05-06 |
| fa7eab5d13 | fix multi currency | 2024-12-02 |
| 9ae66664e4 | set currency and validate | 2024-05-14 |
| d88545580a | add different in base currency | 2024-05-14 |
| 9c4a38ad26 | changed currency preview | 2024-05-14 |
| a47ad0af7e | add multi currency view field | 2024-05-14 |
| 54e4263172 | allow multi currency exchange rate 1 | 2024-04-16 |
| e66404be9a | fix date currency transaction | 2024-04-01 |
| 978a65bd00 | get account by currency | 2024-03-26 |
| f1070a1375 | add settings fx adjustment currency | 2024-03-26 |
| 51ec5c16cf | disable main currency rate | 2024-03-25 |
| 64ed0a4518 | find currency on holiday | 2024-03-14 |
| cce0a7760d | fetch currency | 2024-03-13 |
| 8cdbc40dd1 | add settings for MAS currency rate | 2024-03-13 |
| ff2bb9df08 | calculate base value currency | 2024-02-07 |
| 4447102206 | fix fetch currency | 2023-11-09 |
| 87cc7cf37b | save fetched currency | 2023-11-02 |
| 592eb2feae | refactor: Exchange rate revaluation to handle accounts with zero account balance | 2023-10-03 |
| f2fde8327d | fix: always send account currency in response | 2022-11-17 |
| a26470a65f | fix: incorrect currency in Exchange rate revaluation | 2022-11-17 |
| 9a737afb77 | chore(patch): remove reload_doc from post model sync update_exchange_rate_settings patch | 2022-11-17 |
| a8329cf06b | Multicurrency | 2022-11-10 |
| 3f0b03c0a4 | chore: Use account currency as fallback | 2022-10-24 |
| 195500cb32 | fix: Curreny in SOA print for multi-currency party | 2022-10-24 |

## Affected Files

### Core Exchange Rate Logic
- erpnext/setup/utils.py (get_exchange_rate, get_exchange_rate_from_api, save_currency_exchange)
- erpnext/setup/doctype/currency_exchange/currency_exchange.py

### Currency Exchange Settings
- erpnext/accounts/doctype/currency_exchange_settings/currency_exchange_settings.js
- erpnext/accounts/doctype/currency_exchange_settings/currency_exchange_settings.json
- erpnext/accounts/doctype/currency_exchange_settings/currency_exchange_settings.py

### Exchange Rate Revaluation
- erpnext/accounts/doctype/exchange_rate_revaluation/exchange_rate_revaluation.js
- erpnext/accounts/doctype/exchange_rate_revaluation/exchange_rate_revaluation.json
- erpnext/accounts/doctype/exchange_rate_revaluation/exchange_rate_revaluation.py
- erpnext/accounts/doctype/exchange_rate_revaluation_account/exchange_rate_revaluation_account.json

### Journal Entry Multi-Currency
- erpnext/accounts/doctype/journal_entry/journal_entry.js
- erpnext/accounts/doctype/journal_entry/journal_entry.json
- erpnext/accounts/doctype/journal_entry/journal_entry.py
- erpnext/accounts/doctype/journal_entry_account/journal_entry_account.json

### Accounts Settings
- erpnext/accounts/doctype/accounts_settings/accounts_settings.json
- erpnext/accounts/doctype/account_adjustment_map/

### GL & General Ledger
- erpnext/accounts/doctype/gl_entry/gl_entry.py
- erpnext/accounts/general_ledger.py

### UOB Integration
- erpnext/uob/doctype/payment_approval/payment_approval.js
- erpnext/uob/doctype/payment_approval/payment_approval.json
- erpnext/uob/doctype/payment_approval/payment_approval.py
- erpnext/foms/doctype/uob_file_log/uob_file_log.py

### Other
- erpnext/controllers/va2.py
- erpnext/buying/doctype/purchase_order/purchase_order.py
- erpnext/hooks.py

## Flow/Logic

### 1. Exchange Rate Fetching (`get_exchange_rate()`)
- Entry point: `setup/utils.py:get_exchange_rate(from_currency, to_currency, transaction_date, args, err_journal, from_scheduler, force)`
- Returns 1 if same currency.
- Checks `Currency Exchange Settings` for configuration.

### 2. First-Day-of-Month Rate Logic
- If `use_rate_as_first_day_of_month_rate` is enabled in settings:
  - If transaction_date is the first day of the month, uses the previous day's rate (last day of prior month).
  - Otherwise, uses the first day of the current month's rate.
- This ensures consistent rates throughout a month for accounting purposes.

### 3. Existing Rate Lookup
- Queries `Currency Exchange` records with filters: date <= transaction_date, matching currencies.
- Supports `for_buying` and `for_selling` filters.
- If `allow_stale` is disabled, applies a stale_days window filter.
- If an existing record is found but date doesn't match exactly (or `force=True`), fetches from API anyway.

### 4. MAS API Integration (`get_exchange_rate_from_api1()`)
- Primary provider for Singapore-based operations.
- API endpoint: `eservices.mas.gov.sg/apimg-gw/server/monthly_statistical_bulletin_non610ora/exchange_rates_end_of_period_daily/`
- Handles weekends: skips Saturday/Sunday by incrementing the date offset.
- Retries up to 7 days back if no data is available.
- Parses response using configurable `result_key` path from settings.
- Handles reversed currency pairs (e.g., if USD_SGD not found, tries SGD_USD and inverts).
- Handles `_100` suffix rates (divides by 100 for currencies quoted per 100 units).
- Caches results for 6 hours in Redis.
- Extracts `end_of_day` as the bank_date from the response.

### 5. Frankfurter API Integration (`get_exchange_rate_from_api2()`)
- Secondary/alternative provider.
- API: `https://api.frankfurter.dev/v1/{date}?base={from}&symbols={to}`
- Simpler parsing: directly reads `rates.{to_currency}` from response.
- Also caches for 6 hours.

### 6. Saving Currency Exchange Records (`save_currency_exchange()`)
- After fetching, saves a `Currency Exchange` record if:
  - No duplicate exists for the same date/from/to combination.
  - `save_fetched_currency_exchange_rates` is enabled in Accounts Settings.
- Stores: date, from_currency, to_currency, exchange_rate, fetch_on timestamp, bank_date, from_scheduler flag.

### 7. Currency Exchange Settings DocType
- Configures the API provider: `exchangerate.host`, `frankfurter.app`, or `mas.gov.sg`.
- For MAS: auto-sets the API endpoint and result key path.
- Stores request parameters, header parameters, and result key navigation path.
- Validates connectivity on save by making a test API call.

### 8. Multi-Currency in Journal Entry
- Journal Entry supports multi-currency accounts with per-row exchange rates.
- `account_currency` and `exchange_rate` fields on each journal entry account row.
- Calculates `debit`/`credit` (base currency) from `debit_in_account_currency`/`credit_in_account_currency`.

### 9. UOB Payment Currency Validation
- Validates that payee currency matches the payment currency.
- Shows default currency in payment approval forms.
- Currency field is required for UOB payment processing.

## Dependencies
- Currency Exchange Settings doctype (API configuration)
- Accounts Settings (allow_stale, stale_days, save_fetched_currency_exchange_rates)
- Currency Exchange doctype (stored rate records)
- Redis cache (6-hour TTL for API results)
- External APIs: MAS Singapore, Frankfurter
- Company doctype (default currency)
- Account doctype (account_currency)

## Notes
- The MAS API is the primary provider for this Singapore-based deployment. It handles SGD-centric currency pairs.
- Weekend handling is critical for MAS API since it only provides rates for business days.
- The `use_rate_as_first_day_of_month_rate` setting is a GP-specific feature that locks exchange rates to the first business day of each month for consistency.
- Currency pairs not found directly are attempted in reverse (1/rate) - important for less common pairs.
- The `_100` pattern handles currencies quoted per 100 units (e.g., JPY, IDR).
- The `force` parameter bypasses cached/existing rates and always fetches from API.
- `from_scheduler` flag distinguishes between user-triggered and automated rate fetches.
