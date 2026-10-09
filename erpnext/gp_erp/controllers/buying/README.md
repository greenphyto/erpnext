# controllers/buying/

DocType controller overrides for the Buying module (Purchase Invoice,
Purchase Order, Supplier, Request for Quotation, ...).

## How to use

Same pattern as the parent `controllers/` folder — one `.py` + one
co-located `.js` per doctype (same base name), Python class inherits from
the original controller, JS appends to the doctype's form script.
Registered in `hooks.py:override_doctype_class` (Python) and
`hooks.py:doctype_js` (JS).

```python
# purchase_invoice.py
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice

class PurchaseInvoiceGP(PurchaseInvoice):
    def validate(self):
        super().validate()
        ...
```

```javascript
// purchase_invoice.js — additive only, no super() equivalent
frappe.ui.form.on("Purchase Invoice", {
    validate(frm) {
        ...
    },
});
```

## Planned implementation

Empty for now. Candidate: `purchase_invoice.py` — migrate relevant
`validate` / `on_submit` logic currently living in `doc_events` for
"Purchase Invoice" (see `hooks.py`, pointing to `controllers/erp.py` /
`controllers/foms.py`). `purchase_invoice.js` only if client-side
additions are actually needed.
