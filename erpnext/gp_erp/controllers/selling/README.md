# controllers/selling/

DocType controller overrides for the Selling module (Sales Invoice, Sales
Order, Quotation, Delivery Note, Customer, ...).

## How to use

Same pattern as the parent `controllers/` folder — one `.py` + one
co-located `.js` per doctype (same base name), Python class inherits from
the original controller, JS appends to the doctype's form script.
Registered in `hooks.py:override_doctype_class` (Python) and
`hooks.py:doctype_js` (JS).

```python
# sales_invoice.py
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class SalesInvoiceGP(SalesInvoice):
    def validate(self):
        super().validate()
        ...
```

```javascript
// sales_invoice.js — additive only, no super() equivalent
frappe.ui.form.on("Sales Invoice", {
    validate(frm) {
        ...
    },
});
```

## Planned implementation

Empty for now. Candidate: `sales_invoice.py` — migrate relevant
`validate` / `on_submit` logic currently living in `doc_events` for
"Sales Invoice" (see `hooks.py`, pointing to `controllers/erp.py` /
`controllers/foms.py`). `sales_invoice.js` only if client-side additions
are actually needed.
