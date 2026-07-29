# controllers/

Master folder for DocType controller overrides — both Python
(`override_doctype_class`) and client-side JS (`doctype_js`). Each doctype
gets a co-located `.py` + `.js` pair in the same module subfolder.

- **Python side**: Frappe's native `override_doctype_class` hook, resolved
  in `base_document.py:import_controller()` to swap the default controller
  class of a DocType with a custom subclass. No monkey-patching involved.
- **JS side**: Frappe's native `doctype_js` hook (`meta.py:114`,
  `add_code_via_hook`). Unlike the Python side, this is **additive**, not a
  class swap — the file's content gets appended after the DocType's
  standard JS. There is no `super()` equivalent in JS.

## How to use

1. Pick the ERPNext module the target DocType belongs to (`selling/`,
   `buying/`, `stock/`, `accounts/`, ...). Create the subfolder if it
   doesn't exist yet, mirroring `erpnext/<module>/doctype/` naming so
   anyone familiar with ERPNext can find the file.
2. Create a `.py` file named after the doctype (snake_case), containing a
   class that inherits from the original controller:

   ```python
   # erpnext/gp_erp/controllers/selling/sales_invoice.py
   from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

   class SalesInvoiceGP(SalesInvoice):
       def validate(self):
           super().validate()
           self.custom_validation_logic()
   ```

3. Register it in `hooks.py` under `override_doctype_class`:

   ```python
   override_doctype_class = {
       "Sales Invoice": "erpnext.gp_erp.controllers.selling.sales_invoice.SalesInvoiceGP",
   }
   ```

4. (Optional) Create a `.js` file with the same base name, co-located next
   to the `.py` file, for client-side additions:

   ```javascript
   // erpnext/gp_erp/controllers/selling/sales_invoice.js
   frappe.ui.form.on("Sales Invoice", {
       validate(frm) {
           // additional client-side logic
       },
   });
   ```

5. Register it in `hooks.py` under `doctype_js` (path relative to app
   root, not dotted-module-path):

   ```python
   doctype_js = {
       "Sales Invoice": "gp_erp/controllers/selling/sales_invoice.js",
   }
   ```

That's it. Python-side methods not overridden keep behaving exactly like
the original class (through `super()` chaining, or simply by not existing
in the subclass). JS-side handlers get appended, not swapped.

## Rules

- Always inherit from the original controller class, never rewrite it
  from scratch (Python side).
- Always call `super().<method>()` unless you deliberately want to fully
  replace ERPNext's default behavior for that method (Python side).
- One `.py` + one `.js` file per doctype, same base name, same subfolder.
  Do not stack multiple doctype overrides in a single file.
- JS is additive only. If you need to truly replace an existing handler
  (not just add one), you must rewrite that exact `frappe.ui.form.on(...)`
  handler yourself — check the standard doctype's `.js` source first to
  know what you're overriding and in what load order.
- Existing `doc_events` hooks in `hooks.py` (pointing to
  `controllers/erp.py` / `controllers/foms.py`) remain valid and can run
  alongside `override_doctype_class` — migration to this structure is
  optional and incremental, not a hard requirement.

## Planned implementation

Not yet implemented. First candidates to migrate from `doc_events`
(`erp.py` / `foms.py`) once this structure is adopted:

- Sales Invoice (`selling/`)
- Purchase Invoice (`buying/`)
- Stock Entry (`stock/`)

See `gp_erp/OVERIDE_PLAN_v14.md` (section 3) for full rationale.
