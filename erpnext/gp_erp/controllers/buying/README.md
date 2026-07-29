# controllers/buying/

DocType controller overrides for the Buying module (Purchase Invoice,
Purchase Order, Supplier, Request for Quotation, ...).

## How to use

Same pattern as the parent `controllers/` folder — one file per doctype,
class inherits from the original controller, registered in
`hooks.py:override_doctype_class`.

```python
# purchase_invoice.py
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice

class PurchaseInvoiceGP(PurchaseInvoice):
    def validate(self):
        super().validate()
        ...
```

## Planned implementation

Empty for now. Candidate: `purchase_invoice.py` — migrate relevant
`validate` / `on_submit` logic currently living in `doc_events` for
"Purchase Invoice" (see `hooks.py`, pointing to `controllers/erp.py` /
`controllers/foms.py`).
