# controllers/

Master folder for all DocType override layers — co-located per doctype in
the same module subfolder.  Each doctype can have up to 4 files:

| File | Hook | Layer |
|---|---|---|
| `sales_invoice.py` | `override_doctype_class` | Python controller class |
| `sales_invoice.js` | `doctype_js` | Form-level client script (additive) |
| `sales_invoice_list.js` | `doctype_list_js` | List view config (additive) |
| `sales_invoice_dashboard.py` | `override_doctype_dashboards` | Dashboard metadata (transform dict) |

All four layers can coexist for the same doctype without conflict — they
operate at completely different runtime points (server-side controller,
client-side form handlers, list view config, form sidebar metadata).

## How to use

### 1. Python controller (section 3 of the plan)

Inherit from the original controller class, register in
`hooks.py:override_doctype_class`:

```python
# selling/sales_invoice.py
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class SalesInvoiceGP(SalesInvoice):
    def validate(self):
        super().validate()
        self.custom_validation_logic()
```

```python
override_doctype_class = {
    "Sales Invoice": "erpnext.gp_erp.controllers.selling.sales_invoice.SalesInvoiceGP",
}
```

### 2. Form JS (section 3.5)

Additive client script, registered in `hooks.py:doctype_js`:

```javascript
// selling/sales_invoice.js
frappe.ui.form.on("Sales Invoice", {
    validate(frm) { /* additional logic */ },
});
```

```python
doctype_js = {
    "Sales Invoice": "gp_erp/controllers/selling/sales_invoice.js",
}
```

### 3. List view JS (section 3.7)

Additive list config, registered in `hooks.py:doctype_list_js`:

```javascript
// selling/sales_invoice_list.js
frappe.listview_settings["Sales Invoice"] = {
    add_fields: ["custom_field"],
    onload(listview) { /* custom list actions */ },
};
```

```python
doctype_list_js = {
    "Sales Invoice": ["gp_erp/controllers/selling/sales_invoice_list.js"],
}
```

### 4. Dashboard (section 3.8)

Transform the dashboard metadata dict, registered in
`hooks.py:override_doctype_dashboards`:

```python
# selling/sales_invoice_dashboard.py
from frappe import _

def get_data(data=None):
    if not data:
        data = {}
    data["transactions"] = data.get("transactions", []) + [
        {"label": _("Custom"), "items": ["Custom DocType"]},
    ]
    return data
```

```python
override_doctype_dashboards = {
    "Sales Invoice": "erpnext.gp_erp.controllers.selling.sales_invoice_dashboard.get_data",
}
```

## Rules

- Always inherit from the original controller class, never rewrite from
  scratch (Python side).
- Always call `super().<method>()` unless you deliberately want to fully
  replace ERPNext's default behavior for that method (Python side).
- One file per layer per doctype, same base name, same subfolder.
  Do not stack multiple doctype overrides in a single file.
- JS is additive only. If you need to truly replace an existing handler
  (not just add one), you must rewrite that exact `frappe.ui.form.on(...)`
  handler yourself — check the standard doctype's `.js` source first.
- Dashboard functions must accept `data=None` and merge into the existing
  dict, not return a hardcoded dict that replaces ERPNext's original.
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

See `gp_erp/OVERIDE_PLAN_v14.md` sections 3–3.8 for full rationale.
