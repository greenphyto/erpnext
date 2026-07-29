# controllers/accounts/

DocType controller overrides for the Accounts module (Journal Entry,
Payment Entry, GL Entry, Account, ...).

## How to use

Same pattern as the parent `controllers/` folder — one `.py` + one
co-located `.js` per doctype (same base name), Python class inherits from
the original controller, JS appends to the doctype's form script.
Registered in `hooks.py:override_doctype_class` (Python) and
`hooks.py:doctype_js` (JS).

```python
# payment_entry.py
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

class PaymentEntryGP(PaymentEntry):
    def validate(self):
        super().validate()
        ...
```

```javascript
// payment_entry.js — additive only, no super() equivalent
frappe.ui.form.on("Payment Entry", {
    validate(frm) {
        ...
    },
});
```

## Planned implementation

Empty for now. No specific doctype candidate selected yet — add here
once accounts-related logic in `doc_events` (`controllers/erp.py` /
`controllers/foms.py`) is chosen for migration.
