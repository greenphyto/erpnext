# public/js/controllers/

Global prototype monkey-patches for ERPNext's base JS controller classes
(`erpnext.taxes_and_totals`, `erpnext.TransactionController`).

## Why this folder exists

`taxes_and_totals.js` and `transaction.js` are NOT per-doctype scripts.
They are shared base classes loaded on **every page** via
`erpnext.bundle.js` (wired through `hooks.py:app_include_js`).  Every
transactional doctype (Sales Invoice, Purchase Invoice, Stock Entry,
Delivery Note, Sales Order, Purchase Order, ...) inherits from
`TransactionController` through the prototype chain:

```
erpnext.payments
  └── erpnext.taxes_and_totals
        └── erpnext.TransactionController
              ├── SellingController
              │     ├── SalesInvoiceController
              │     ├── SalesOrderController ...
              └── BuyingController
                    ├── PurchaseOrderController ...
```

`doctype_js` (section 3.5 of the plan) does NOT apply here — these classes
must be available on every page, not just when a specific doctype form
opens.  The only extension point is prototype monkey-patching after the
class is defined.

## How to use

1.  Save a reference to the original prototype method.
2.  Reassign `ClassName.prototype.methodName`.
3.  Call the original via `.call(this, ...)` where custom logic injection
    is needed.

```javascript
// transaction_patch.js
(function () {
    const _original = erpnext.TransactionController.prototype.calculate_taxes_and_totals;

    erpnext.TransactionController.prototype.calculate_taxes_and_totals =
        async function (update_paid_amount) {
            await _original.call(this, update_paid_amount);
            // custom logic added on top
        };
})();
```

## Rules

- Do NOT replace the entire class definition — only patch specific
  prototype methods.
- Always preserve a reference to the original and call it.
- One method patch per IIFE block.  Group related patches for the same
  prototype in the same file.
- Test every patched method in at least one doctype form that inherits
  from the patched class (e.g. if you patch
  `TransactionController.prototype.validate`, test in both Sales Invoice
  and Purchase Invoice since they both inherit it).
- If a subclass defines its own version of the same method (e.g.
  `SellingController.calculate_taxes_and_totals`), the subclass's
  definition has priority over your prototype patch of the parent class.
  In that case, patch the subclass prototype instead.

## Wiring

Add paths to `hooks.py:app_include_js` AFTER `"erpnext.bundle.js"` so they
load after the base classes are defined:

```python
app_include_js = [
    "erpnext.bundle.js",
    "/assets/erpnext/js/company_view.js",
    "/assets/erpnext/js/gp_erp/controllers/transaction_patch.js",
    "/assets/erpnext/js/gp_erp/controllers/taxes_and_totals_patch.js",
]
```

No `build.json` or esbuild entry needed — raw asset symlinks handle this
via the app root path convention.

## Difference from gp_erp/controllers/

| Aspect | `gp_erp/controllers/` | `public/js/controllers/` |
|---|---|---|
| Target | Per-doctype Python class + JS handlers | Global base JS controller classes |
| Hook | `override_doctype_class` + `doctype_js` | `app_include_js` |
| Mechanism | Native `super()` (Python) / additive `frappe.ui.form.on()` (JS) | Prototype monkey-patch |
| Scope | One doctype (e.g. Sales Invoice only) | All doctypes inheriting the patched base class |
| Load timing | Form-open (doctype metadata) | Every page load (app bundle) |

## Planned implementation

Empty for now.  First candidates when needed:

- `transaction_patch.js` — `TransactionController.prototype` patches for
  cross-cutting custom logic (`calculate_taxes_and_totals`, `item_code`,
  `rate`, `validate`, ...).
- `taxes_and_totals_patch.js` — `TaxesAndTotals.prototype` patches for
  tax calculation customizations.

Create each file only when the need actually arises — do not create them in
advance "just in case."

See `gp_erp/OVERIDE_PLAN_v14.md` (section 3.6) for full rationale.
