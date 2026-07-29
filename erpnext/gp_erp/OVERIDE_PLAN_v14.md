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
├── controllers/                     # MASTER controller folder — entry point for override_doctype_class + doctype_js + doctype_list_js
│   ├── __init__.py
│   ├── selling/
│   │   ├── __init__.py
│   │   ├── sales_invoice.py         # class SalesInvoiceGP(SalesInvoice): ...
│   │   ├── sales_invoice.js         # frappe.ui.form.on("Sales Invoice", {...}) — co-located, same name
│   │   └── sales_invoice_list.js    # frappe.listview_settings["Sales Invoice"] — list view override
│   ├── buying/
│   │   ├── __init__.py
│   │   ├── purchase_invoice.py      # class PurchaseInvoiceGP(PurchaseInvoice): ...
│   │   ├── purchase_invoice.js
│   │   └── purchase_invoice_list.js
│   ├── stock/
│   │   ├── __init__.py
│   │   ├── stock_entry.py           # class StockEntryGP(StockEntry): ...
│   │   ├── stock_entry.js
│   │   └── stock_entry_list.js
│   └── accounts/
│       ├── __init__.py
│       └── ...
│
├── public/js/controllers/           # NEW — global prototype monkey-patches for base-controller JS classes
│   ├── README.md
│   ├── transaction_patch.js         # patches erpnext.TransactionController.prototype
│   └── taxes_and_totals_patch.js    # patches erpnext.taxes_and_totals.prototype
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

## 3.6. Global Controller Patch — Prototype Monkey-Patch for Base JS Classes

**Different problem from section 3.5:** `taxes_and_totals.js` and `transaction.js` are NOT per-doctype scripts. They are shared base classes loaded globally on EVERY page via `erpnext.bundle.js`, which is wired through `hooks.py:app_include_js` (not `doctype_js`). The JS class chain looks like this:

```
erpnext.payments
  └── erpnext.taxes_and_totals          (public/js/controllers/taxes_and_totals.js)
        └── erpnext.TransactionController  (public/js/controllers/transaction.js)
              ├── erpnext.selling.SellingController   (selling/sales_common.js)
              │     ├── SalesInvoiceController   (sales_invoice.js)
              │     ├── SalesOrderController      (sales_order.js)
              │     └── ...
              └── erpnext.buying.BuyingController    (public/js/controllers/buying.js)
                    ├── PurchaseOrderController  (purchase_order.js)
                    └── ...
```

Every transactional doctype (Sales Invoice, Purchase Invoice, Stock Entry, Delivery Note, Sales Order, Purchase Order, Quotation, Purchase Receipt...) instantiates one of these subclasses via `extend_cscript(cur_frm.cscript, new XxxController({frm: cur_frm}))` at the bottom of its own `.js` file. The base `TransactionController` and `TaxesAndTotals` methods are called through prototype-chain resolution at runtime — so patching their prototypes affects every doctype that inherits them.

**Why `doctype_js` doesn't work here:** `doctype_js` files get inlined into a doctype's `__js` metadata and loaded only when that specific doctype's form opens. Base classes like `taxes_and_totals.js` need to be available on every page (including non-doctype pages like reports, dashboards) because other bundles and doctype scripts reference `erpnext.TransactionController` and `erpnext.taxes_and_totals` directly.

**Pattern** (save original prototype ref before overwriting — manual `super()` equivalent):

```javascript
// erpnext/gp_erp/public/js/controllers/transaction_patch.js
(function () {
    const _original_calculate_taxes_and_totals =
        erpnext.TransactionController.prototype.calculate_taxes_and_totals;

    erpnext.TransactionController.prototype.calculate_taxes_and_totals =
        async function (update_paid_amount) {
            await _original_calculate_taxes_and_totals.call(this, update_paid_amount);
            // custom logic added on top of original behavior
        };
})();
```

This works because JavaScript prototype lookup is dynamic at call-time, not fixed at class-definition time. The subclass (e.g. `SalesInvoiceController`) inherits the patched prototype, and any `super.calculate_taxes_and_totals()` call inside the subclass resolves against the patched version — there is no "frozen" reference at `extends` time. The only case this doesn't cover is if a subclass defines the same method itself (overriding at subclass level); then you'd need to patch that specific subclass prototype instead.

**Wiring** — append path to `app_include_js` in `hooks.py`, AFTER `"erpnext.bundle.js"` so it loads after the base classes are defined:

```python
app_include_js = [
    "erpnext.bundle.js",
    "/assets/erpnext/js/company_view.js",
    "/assets/erpnext/js/gp_erp/controllers/transaction_patch.js",
    "/assets/erpnext/js/gp_erp/controllers/taxes_and_totals_patch.js",
]
```

Path format: `"/assets/erpnext/js/..."` — same convention as `company_view.js` already in `app_include_js`. No need to add to `build.json` or esbuild config; raw asset paths work via `app_include_js`.

**Coexistence with section 3.5 (doctype_js):** Both mechanisms can be used together for the same doctype. `doctype_js` adds per-doctype handlers (`frappe.ui.form.on("Sales Invoice", ...)`). Global prototype patches affect the base controller class methods (`TransactionController.prototype.calculate_taxes_and_totals`). They operate at different layers — prototype chain vs. event-handler list — and don't conflict.

**Coexistence with section 3 (override_doctype_class):** No interaction — `override_doctype_class` is Python-side, these patches are JS-side. They target different runtime environments entirely.

**Future candidates (not implemented yet):**
- `transaction_patch.js` — patch `calculate_taxes_and_totals`, `item_code`, `rate`, etc. on `TransactionController.prototype`
- `taxes_and_totals_patch.js` — patch `apply_discount_amount`, `set_item_wise_tax`, etc. on `TaxesAndTotals.prototype`

---

## 3.7. List View JS — `doctype_list_js` Hook

**Mechanism:** Same as `doctype_js` (section 3.5) — additive, not a replacement. Frappe loads `<doctype_name>_list.js` from the doctype's own folder by convention (`meta.py:103`), then appends additional files registered via `doctype_list_js` hook (`meta.py:115`). The underlying data structure is `frappe.listview_settings["<Doctype>"]` — a plain JS object that configures columns, indicators, and list view actions. Adding more properties to this object extends the list view behavior without conflicts.

**Files follow the same co-location pattern:** one `*_list.js` file per doctype, same subfolder as the `.py` + `.js` pair, distinguished by the `_list` suffix.

**Pattern:**
```javascript
// erpnext/gp_erp/controllers/buying/purchase_invoice_list.js
frappe.listview_settings["Purchase Invoice"] = {
    // merge these properties into the existing listview_settings object;
    // Frappe merges them additively — properties you don't set stay from
    // the original file.
    add_fields: ["custom_field_1", "custom_field_2"],
    onload(listview) {
        // custom list view actions (buttons, filters)
    },
};
```

**Wiring** (one entry per doctype in `hooks.py`, dict already exists, just add to it):

```python
doctype_list_js = {
    "Code List": ["edi/doctype/code_list/code_list_import.js"],
    "Common Code": ["edi/doctype/code_list/code_list_import.js"],
    "Purchase Invoice": ["gp_erp/controllers/buying/purchase_invoice_list.js"],
}
```

**If you need to override an existing method** like `get_indicator` from the original `_list.js` (not just add properties), the additive merge alone won't replace it — Frappe does a shallow `$.extend` on `listview_settings`, so both original and custom `get_indicator` functions would interact unpredictably. Use prototype-style save-and-replace on the `listview_settings` object instead:

```javascript
(function () {
    const _original_get_indicator =
        frappe.listview_settings["Purchase Invoice"].get_indicator;

    frappe.listview_settings["Purchase Invoice"].get_indicator = function (doc) {
        // custom logic
        return _original_get_indicator ? _original_get_indicator.call(this, doc) : null;
    };
})();
```

**Difference from `doctype_js` (section 3.5):** `doctype_js` appends to form-level event handlers (`frappe.ui.form.on("Sales Invoice", ...)`). `doctype_list_js` appends to list-view configuration (`frappe.listview_settings["Sales Invoice"]`). Different endpoints, but the same additive hook mechanism. Both files are co-located in the same module subfolder.

**Coexistence:** All three JS layers can be used together for the same doctype without conflict:
- `*_list.js` → list view behavior
- `*.js` (via `doctype_js`) → form behavior
- `*_patch.js` (via `app_include_js`) → global base class behavior

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
- "True override" for per-doctype JS event handlers (section 3.5) — no native hook exists, and the reimplementation approach is entirely different (rewrite the full event handler, no `super()`). Handle it case-by-case if/when the need arises, instead of building a generic abstraction upfront.

---

## 6. Verification

- DocType override: `bench --site test5 console` → `frappe.get_doc("Sales Invoice").__class__.__name__` should be `SalesInvoiceGP`.
- Client Script (section 3.5): open the Sales Invoice form in the browser, check that `sales_invoice.js` is loaded (network tab / `frm.script_type`, or drop a temporary `console.log`) — confirm no errors and that ERPNext's original handlers still run.
- Global controller patch (section 3.6): open any transactional doctype form (e.g. Sales Invoice) after deploying `transaction_patch.js`, open browser console — confirm the patched method runs (e.g. drop a `console.log` in the patch body), confirm no errors, confirm original behavior still works.
- Report override: `bench --site test5 execute erpnext.gp_erp.report_pacthing.report_override.apply`, then run the report from the UI and check the modified result.
- A small self-check assertion is left in `report_override.py` (e.g. `assert report_module.get_report_module_dotted_path is _patched` called once after `apply()`).
