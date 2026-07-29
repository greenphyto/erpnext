# report_controllers/

Overrides for the *logic* of existing ERPNext reports (not `gp_erp`'s own
reports — those live in `gp_erp/report/`). Paired with `report_pacthing/`,
which does the actual redirect.

## How to use

1. Add an entry to `registry.py` mapping the exact report name to this
   package's dotted module path:

   ```python
   # registry.py
   REPORT_OVERRIDES = {
       "Delivery Note Trends": "erpnext.gp_erp.report_controllers.delivery_note_trends",
   }
   ```

2. Create a module here with the exact same contract Frappe expects from
   any report script — a top-level `execute(filters=None)` function
   returning `(columns, data)`:

   ```python
   # delivery_note_trends.py
   def execute(filters=None):
       from erpnext.stock.report.delivery_note_trends.delivery_note_trends import execute as original_execute
       columns, data = original_execute(filters)
       # custom logic here
       return columns, data
   ```

That's it — `report_pacthing/report_override.py` handles making Frappe
resolve to this module instead of the original one.

## Rules

- Report name in `registry.py` must match exactly (case-sensitive) the
  `Report` doctype's `name` field.
- Always wrap/reuse the original `execute()` when possible instead of
  reimplementing report logic from scratch.
- Reports not listed in `registry.py` are completely unaffected — the
  patch falls back to Frappe's original path resolution.

## Planned implementation

Empty for now. First candidate: `delivery_note_trends.py` (see
`gp_erp/OVERIDE_PLAN_v14.md`, section 4, for full rationale). `registry.py`
itself also not yet created — create it together with the first override.
