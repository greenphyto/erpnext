# Request Calendar

## Summary
Visual calendar view for the Request doctype using FullCalendar, with item code filter cards, color-coded events by item prefix and docstatus, and a scrollable card strip for quick filtering.

## Commits
| Hash | Message | Date |
|------|---------|------|
| 024065005a | change to delivery date on request calendar | 2026-06-26 |
| 96f30d0b4d | request calendar v1.2 fix event style | 2026-06-25 |
| 9203ce4a1a | calendar request v1.1, filter card click and filter | 2026-06-25 |
| d1c5005993 | calendar request (init) | 2026-06-25 |

## Affected Files
- erpnext/buying/doctype/request/request.json
- erpnext/buying/doctype/request/request.py
- erpnext/buying/doctype/request/request_calendar.js

## Flow/Logic
1. `request_calendar.js` registers `frappe.views.calendar["Request"]` with field mappings (`start`/`end` mapped to delivery_date), style map (Draft=orange, Submit=green), and calendar options (06:00-20:00, 30min slots).
2. The `get_events_method` points to `erpnext.buying.doctype.request.request.get_events`.
3. `get_events()` in `request.py` queries Request + Request Items (inner join) filtering by docstatus != 2. It supports optional `item_codes` filter passed as JSON array, building parameterized IN clause.
4. Each event title is formatted as `"{item_code} - {weight} Kg"` with `package_size` shown as secondary info.
5. Event colors are determined by `get_event_color()` based on item_code prefix:
   - `PR-AV`: yellow (#FFC107) when submitted, pink (#EC008C) when draft
   - `PR-LV`: green (#28A745) when submitted, cyan (#00FFFF) when draft
   - `PR-HV`: blue (#007BFF) when submitted, purple (#934FA7) when draft
   - Default: gray (#6C757D)
6. The JS patches `frappe.views.Calendar.prototype` methods:
   - `get_args`: injects `item_codes` custom filter into calendar fetch args.
   - `prepare_colors`: preserves backend `textColor` hex values.
   - `setup_options` / `eventRender`: renders two-line event display (title + department/package_size).
7. `RequestCards` class renders a horizontal scrollable card strip above the calendar:
   - Fetches data via `get_request_items()` which returns distinct item_codes from submitted Requests with counts and total weight (current year).
   - Cards show item_code, department, total weight, and request count.
   - Clicking a card toggles item_code in `_custom_filters.item_codes[]` and triggers `refetchEvents`.
   - Selected filters are rendered as colored tags in the FullCalendar toolbar.
   - "Show All" opens a dialog with searchable card grid for all items.
   - Search input filters visible cards by item_code or item_name substring match.

## Dependencies
- Frappe Calendar view (`frappe.views.Calendar`)
- FullCalendar library (bundled with Frappe)
- Request doctype and Request Items child table

## Notes
- Calendar uses `delivery_date` as both start and end (all-day events).
- Card color coding matches event color coding by item_code prefix.
- The `get_request_items` endpoint only returns items from the current year (`YEAR(r.posting_date) = YEAR(CURDATE())`).
- Multiple item_codes can be selected simultaneously (multi-select toggle behavior).
