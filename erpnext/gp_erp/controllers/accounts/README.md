# controllers/accounts/

DocType controller overrides for the Accounts module (Journal Entry,
Payment Entry, GL Entry, Account, ...).

## How to use

Same pattern as the parent `controllers/` folder — one file per doctype,
class inherits from the original controller, registered in
`hooks.py:override_doctype_class`.

```python
# payment_entry.py
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

class PaymentEntryGP(PaymentEntry):
    def validate(self):
        super().validate()
        ...
```

## Planned implementation

Empty for now. No specific doctype candidate selected yet — add here
once accounts-related logic in `doc_events` (`controllers/erp.py` /
`controllers/foms.py`) is chosen for migration.
