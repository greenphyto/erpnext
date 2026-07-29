# controllers/

Master folder for DocType controller overrides via Frappe's native
`override_doctype_class` hook. This is the entry point Frappe uses in
`base_document.py:import_controller()` to swap the default controller class
of a DocType with a custom subclass — no monkey-patching involved.

## How to use

1. Pick the ERPNext module the target DocType belongs to (`selling/`,
   `buying/`, `stock/`, `accounts/`, ...). Create the subfolder if it
   doesn't exist yet, mirroring `erpnext/<module>/doctype/` naming so
   anyone familiar with ERPNext can find the file.
2. Create a file named after the doctype (snake_case), containing a class
   that inherits from the original controller:

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

That's it. Any method not overridden keeps behaving exactly like the
original class (through `super()` chaining, or simply by not existing in
the subclass).

## Rules

- Always inherit from the original controller class, never rewrite it
  from scratch.
- Always call `super().<method>()` unless you deliberately want to fully
  replace ERPNext's default behavior for that method.
- One file per doctype. Do not stack multiple doctype overrides in a
  single file.
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
