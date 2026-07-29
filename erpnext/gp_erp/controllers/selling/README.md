# controllers/selling/

DocType controller overrides for the Selling module (Sales Invoice, Sales
Order, Quotation, Delivery Note, Customer, ...).

## How to use

Same pattern as the parent `controllers/` folder — one file per doctype,
class inherits from the original controller, registered in
`hooks.py:override_doctype_class`.

```python
# sales_invoice.py
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class SalesInvoiceGP(SalesInvoice):
    def validate(self):
        super().validate()
        ...
```

## Planned implementation

Empty for now. Candidate: `sales_invoice.py` — migrate relevant
`validate` / `on_submit` logic currently living in `doc_events` for
"Sales Invoice" (see `hooks.py`, pointing to `controllers/erp.py` /
`controllers/foms.py`).
