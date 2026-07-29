# controllers/stock/

DocType controller overrides for the Stock module (Stock Entry, Delivery
Note, Warehouse, Item, ...).

## How to use

Same pattern as the parent `controllers/` folder — one `.py` + one
co-located `.js` per doctype (same base name), Python class inherits from
the original controller, JS appends to the doctype's form script.
Registered in `hooks.py:override_doctype_class` (Python) and
`hooks.py:doctype_js` (JS).

```python
# stock_entry.py
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry

class StockEntryGP(StockEntry):
    def validate(self):
        super().validate()
        ...
```

```javascript
// stock_entry.js — additive only, no super() equivalent
frappe.ui.form.on("Stock Entry", {
    validate(frm) {
        ...
    },
});
```

## Planned implementation

Empty for now. Candidate: `stock_entry.py` — migrate relevant `validate`
/ `on_submit` / `on_cancel` logic currently living in `doc_events` for
"Stock Entry" (see `hooks.py`, pointing to `controllers/erp.py` /
`controllers/foms.py`, e.g. `detect_salad_items`,
`check_missing_se_rate`, `sync_sle`). `stock_entry.js` only if
client-side additions are actually needed.
