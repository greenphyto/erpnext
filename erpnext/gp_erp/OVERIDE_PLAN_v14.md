# Plan: Master Controller Override System — `gp_erp`

**Branch target:** `v14.3.1-origin-ready`
**Current status:** `override_doctype_class` is only used by default ERPNext for `Address`. All existing customization is stacked in `doc_events` (hooks.py) + `controllers/erp.py` (1705 lines) + `controllers/foms.py` (2632 lines). Report override only has `custom_export_report` (xlsx post-process only, not logic override).

---

## 1. Core Concept

Two different mechanisms because Frappe has a native hook for one, but not for the other:

| Target | Mechanism | Reason |
|---|---|---|
| DocType Controller | `override_doctype_class` (native Frappe hook) | Already exists in `base_document.py:import_controller()`, used by ERPNext itself for `Address`. No monkey-patch needed, just register in hooks.py. |
| Report Controller | Monkey-patch `get_report_module_dotted_path` | Frappe has NO hook to redirect a report module's dotted path. The only extension point (`custom_export_report`) is xlsx post-process only, not an `execute()` override. |

This is not "monkey-patch everything" — it's native hook when available, monkey-patch only when there's genuinely no other way (ladder rung 3 vs rung 6).

---

## 2. Folder Hierarchy

```
erpnext/gp_erp/
│
├── controllers/                     # MASTER controller folder — entry point for override_doctype_class + doctype_js
│   ├── __init__.py
│   ├── selling/
│   │   ├── __init__.py
│   │   ├── sales_invoice.py         # class SalesInvoiceGP(SalesInvoice): ...
│   │   └── sales_invoice.js         # frappe.ui.form.on("Sales Invoice", {...}) — co-located, same name
│   ├── buying/
│   │   ├── __init__.py
│   │   ├── purchase_invoice.py      # class PurchaseInvoiceGP(PurchaseInvoice): ...
│   │   └── purchase_invoice.js
│   ├── stock/
│   │   ├── __init__.py
│   │   ├── stock_entry.py           # class StockEntryGP(StockEntry): ...
│   │   └── stock_entry.js
│   └── accounts/
│       ├── __init__.py
│       └── ...
│
├── report_controllers/              # NEW — overrides the logic of EXISTING ERPNext reports (not gp_erp's own reports)
│   ├── __init__.py
│   ├── registry.py                  # single source of truth: {report_name: dotted_module_path}
│   └── delivery_note_trends.py      # def execute(filters=None): ... (signature identical to standard Frappe)
│
├── report_pacthing/                 # NEW — small infra to apply the report patch
│   ├── __init__.py                  # apply() is called once from erpnext/__init__.py
│   └── report_override.py           # patches get_report_module_dotted_path
│
├── doctype/                         # EXISTING, unchanged — new doctypes owned by gp_erp itself
│   ├── ai_agent_memory/
│   ├── consignment_request/
│   └── ...
│
├── report/                          # EXISTING, unchanged — reports 100% owned by gp_erp
│   ├── budget_variance_greenphyto/
│   └── p&l_performance_review/
│
├── custom/                          # EXISTING — custom field json
├── notification/                    # EXISTING
├── print_format/                    # EXISTING
```

**Why split `controllers/` per-module (selling/buying/stock/accounts)?** Because the existing `doc_events` in hooks.py already shows the pattern: overrides are spread across many ERPNext modules (Sales Invoice, Purchase Invoice, Stock Entry, Delivery Note, Asset, Customer, Supplier, Warehouse...). Mirroring the `erpnext/<module>/doctype/` structure lets anyone familiar with ERPNext find the file immediately. If it turns out only 2-3 files total are ever needed, the per-module folders can be flattened later — but given the projected number of doctypes to override (see the existing `doc_events` list), a modular structure is more maintainable from the start.

---

## 3. DocType Controller Override Flow

**Pattern** (copied exactly from `erpnext/accounts/custom/address.py`, which is already proven working):

```python
# erpnext/gp_erp/controllers/selling/sales_invoice.py
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class SalesInvoiceGP(SalesInvoice):
    def validate(self):
        super().validate()
        self.custom_validation_logic()

    def custom_validation_logic(self):
        ...
```

**Wiring** (one line per doctype in `hooks.py`, dict already exists, just add to it):

```python
override_doctype_class = {
    "Address": "erpnext.accounts.custom.address.ERPNextAddress",
    "Sales Invoice": "erpnext.gp_erp.controllers.selling.sales_invoice.SalesInvoiceGP",
    "Purchase Invoice": "erpnext.gp_erp.controllers.buying.purchase_invoice.PurchaseInvoiceGP",
    "Stock Entry": "erpnext.gp_erp.controllers.stock.stock_entry.StockEntryGP",
}
```

Zero monkey-patch. Frappe resolves this automatically in `import_controller()` (base_document.py:89-97). Methods that aren't overridden keep working exactly as before, through `super()`.

**Migration from existing `doc_events` (optional, incremental):** Logic currently spread across `controllers/erp.py` / `controllers/foms.py` and wired via `doc_events` CAN be moved into the controller class if it's a method-level hook (`validate`, `on_submit`, etc.) — but full migration is NOT mandatory. `doc_events` remains valid alongside `override_doctype_class`; both run together without conflict.

---

## 3.5. Client Script (JS) Flow — Co-located with the Python Controller

**Different nature than `override_doctype_class`:** Frappe's JS hook (`doctype_js`) is **additive**, not a replacement. Frappe appends the JS file's content to the doctype's `__js` after the standard JS has already run (`meta.py:114`, `add_code_via_hook`) — not a class swap like `import_controller()` does for Python. So there's no real "override" on the JS side without reimplementing the exact same `frappe.ui.form.on(...)` handler (the effect is adding/overwriting an event listener, not inheriting a class).

**Why is the JS file co-located in the same folder with the same name as its Python file (`sales_invoice.py` + `sales_invoice.js`)?** So anyone opening `controllers/selling/` immediately sees the py+js pair for the same doctype — in one place, instead of split off to a `public/js/` folder far from the controller logic.

**Pattern** (example: adding client-side validation, not overwriting existing ERPNext handlers):

```javascript
// erpnext/gp_erp/controllers/selling/sales_invoice.js
frappe.ui.form.on("Sales Invoice", {
    validate(frm) {
        // additional custom client-side logic
    },
});
```

**Wiring** (one line per doctype in `hooks.py:doctype_js`, dict already exists from default ERPNext, just add to it):

```python
doctype_js = {
    "Address": "public/js/address.js",
    "Communication": "public/js/communication.js",
    "Event": "public/js/event.js",
    "Newsletter": "public/js/newsletter.js",
    "Contact": "public/js/contact.js",
    "Sales Invoice": "gp_erp/controllers/selling/sales_invoice.js",
    "Purchase Invoice": "gp_erp/controllers/buying/purchase_invoice.js",
    "Stock Entry": "gp_erp/controllers/stock/stock_entry.js",
}
```

Paths in `doctype_js` are relative to the app root (`frappe.get_app_path`), not a dotted-module-path like Python — that's why it's `gp_erp/controllers/...` instead of `erpnext.gp_erp.controllers...`.

**Important note:** If you need to truly replace an existing handler's behavior (not just add to it), you still have to rewrite that exact same handler (`frappe.ui.form.on("Sales Invoice", { field_name(frm) {...} })` — the last event registered for the same field runs/overwrites depending on load order; there is NO `super()` equivalent on the JS side). For this case, check the standard ERPNext doctype's `.js` source first to know the order and content of the handler you're overwriting.

---

## 4. Report Controller Override Flow

**Technical problem:** `Report.execute_module()` (frappe/core/doctype/report/report.py:191-195) builds a deterministic path:
```python
method_name = get_report_module_dotted_path(module, self.name) + ".execute"
frappe.get_attr(method_name)(filters)
```
`get_report_module_dotted_path` is just a regular function in the same module — it can be monkey-patched at module-level, and `execute_module` will automatically use the patched version because Python resolves the function name at call-time through the module namespace.

**registry.py** (single source of truth, similar style to `override_doctype_class`):
```python
REPORT_OVERRIDES = {
    "Delivery Note Trends": "erpnext.gp_erp.report_controllers.delivery_note_trends",
}
```

**report_override.py** (minimal patch, ~10 lines, doesn't touch behavior of reports not registered):
```python
import frappe.core.doctype.report.report as report_module
from erpnext.gp_erp.report_controllers.registry import REPORT_OVERRIDES

_original = report_module.get_report_module_dotted_path

def _patched(module, report_name):
    return REPORT_OVERRIDES.get(report_name) or _original(module, report_name)

def apply():
    report_module.get_report_module_dotted_path = _patched
```

**delivery_note_trends.py** (signature must exactly match the Frappe contract — `execute(filters=None)` returning `(columns, data)`):
```python
def execute(filters=None):
    from erpnext.stock.report.delivery_note_trends.delivery_note_trends import execute as original_execute
    columns, data = original_execute(filters)
    # additional custom logic
    return columns, data
```

**Entry point where the patch is called:** one line in `erpnext/__init__.py` (a file that's GUARANTEED to be imported when Frappe boots the app, unlike `gp_erp/__init__.py`, which is only imported lazily when its doctype gets accessed):
```python
from erpnext.gp_erp.report_pacthing import report_override
report_override.apply()
```

---

## 5. What's NOT Being Built Now (skip)

- JSON override — optional/possible via Customize Form / custom field json (`gp_erp/custom/`), the mechanism already exists, no new system needed.
- Registry abstraction for DocType controllers (not needed — the `hooks.py` dict is already enough, native, single file, no reinventing the wheel).
- "True override" for JS (non-additive) — no native hook exists, and the reimplementation approach is entirely different (rewrite the full event handler, no `super()`). Handle it case-by-case if/when the need arises, instead of building a generic abstraction upfront.

---

## 6. Verification

- DocType override: `bench --site test5 console` → `frappe.get_doc("Sales Invoice").__class__.__name__` should be `SalesInvoiceGP`.
- Client Script: open the Sales Invoice form in the browser, check that `sales_invoice.js` is loaded (network tab / `frm.script_type`, or drop a temporary `console.log`) — confirm no errors and that ERPNext's original handlers still run.
- Report override: `bench --site test5 execute erpnext.gp_erp.report_pacthing.report_override.apply`, then run the report from the UI and check the modified result.
- A small self-check assertion is left in `report_override.py` (e.g. `assert report_module.get_report_module_dotted_path is _patched` called once after `apply()`).
