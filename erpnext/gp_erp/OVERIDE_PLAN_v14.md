# Rencana: Master Controller Override System — `gp_erp`

**Branch target:** `v14.3.1-origin-ready`
**Status saat ini:** `override_doctype_class` cuma dipakai default ERPNext buat `Address`. Semua customization existing numpuk di `doc_events` (hooks.py) + `controllers/erp.py` (1705 baris) + `controllers/foms.py` (2632 baris). Report override cuma ada `custom_export_report` (post-process xlsx doang, bukan override logic).

---

## 1. Konsep Inti

Dua mekanisme berbeda karena Frappe punya native hook buat satu, tapi tidak buat yang lain:

| Target | Mekanisme | Alasan |
|---|---|---|
| DocType Controller | `override_doctype_class` (hook native Frappe) | Sudah ada di `base_document.py:import_controller()`, dipakai ERPNext sendiri buat `Address`. Tidak perlu monkey-patch, tinggal daftar di hooks.py. |
| Report Controller | Monkey-patch `get_report_module_dotted_path` | Frappe TIDAK punya hook buat redirect dotted-path report module. Satu-satunya extension point (`custom_export_report`) cuma post-process xlsx, bukan override `execute()`. |

Ini bukan "monkey patch semua", tapi pakai native hook kalau ada, monkey-patch kalau memang tidak ada jalan lain (ladder rung 3 vs rung 6).

---

## 2. Folder Hierarchy

```
erpnext/gp_erp/
│
├── controllers/                     # MASTER controller folder — pintu masuk override_doctype_class
│   ├── __init__.py
│   ├── selling/
│   │   ├── __init__.py
│   │   └── sales_invoice.py         # class SalesInvoiceGP(SalesInvoice): ...
│   ├── buying/
│   │   ├── __init__.py
│   │   └── purchase_invoice.py      # class PurchaseInvoiceGP(PurchaseInvoice): ...
│   ├── stock/
│   │   ├── __init__.py
│   │   └── stock_entry.py           # class StockEntryGP(StockEntry): ...
│   └── accounts/
│       ├── __init__.py
│       └── ...
│
├── report_controllers/              # NEW — override logic report ERPNext EXISTING (bukan report gp_erp sendiri)
│   ├── __init__.py
│   ├── registry.py                  # single source of truth: {report_name: dotted_module_path}
│   └── delivery_note_trends.py      # def execute(filters=None): ... (signature sama persis standar Frappe)
│
├── report_pacthing/                 # NEW — infra kecil buat apply patch report
│   ├── __init__.py                  # apply() dipanggil sekali dari erpnext/__init__.py
│   └── report_override.py           # patch get_report_module_dotted_path
│
├── doctype/                         # EXISTING, tidak berubah — doctype baru milik gp_erp sendiri
│   ├── ai_agent_memory/
│   ├── consignment_request/
│   └── ...
│
├── report/                          # EXISTING, tidak berubah — report yang 100% milik gp_erp
│   ├── budget_variance_greenphyto/
│   └── p&l_performance_review/
│
├── custom/                          # EXISTING — custom field json
├── notification/                    # EXISTING
├── print_format/                    # EXISTING
│
└── (placeholder, fase berikutnya, TIDAK dibuat sekarang)
    public/js/controllers/           # future: override doctype_js, mirror struktur controllers/ di atas
```

**Kenapa `controllers/` dipecah per-module (selling/buying/stock/accounts)?** Karena `doc_events` existing di hooks.py sudah nunjukin pola: override tersebar di banyak modul ERPNext (Sales Invoice, Purchase Invoice, Stock Entry, Delivery Note, Asset, Customer, Supplier, Warehouse...). Mirror struktur `erpnext/<module>/doctype/` bikin siapapun yang familiar ERPNext langsung nemu file-nya. Kalau nanti cuma butuh 2-3 file total, folder per-module boleh diratakan — tapi dengan proyeksi jumlah doctype yang bakal di-override (liat daftar `doc_events` yang sudah ada), struktur modular lebih maintainable dari awal.

---

## 3. Alur DocType Controller Override

**Pattern** (copy exact dari `erpnext/accounts/custom/address.py` yang sudah proven jalan):

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

**Wiring** (satu baris per doctype di `hooks.py`, dict sudah ada, tinggal nambah):

```python
override_doctype_class = {
    "Address": "erpnext.accounts.custom.address.ERPNextAddress",
    "Sales Invoice": "erpnext.gp_erp.controllers.selling.sales_invoice.SalesInvoiceGP",
    "Purchase Invoice": "erpnext.gp_erp.controllers.buying.purchase_invoice.PurchaseInvoiceGP",
    "Stock Entry": "erpnext.gp_erp.controllers.stock.stock_entry.StockEntryGP",
}
```

Nol monkey-patch. Frappe resolve ini otomatis di `import_controller()` (base_document.py:89-97). Method yang tidak di-override tetap jalan seperti asli lewat `super()`.

**Migrasi dari `doc_events` existing (opsional, bertahap):** Logic yang sekarang nyebar di `controllers/erp.py` / `controllers/foms.py` dan didaftarkan via `doc_events` BISA dipindah ke controller class kalau memang method-level hook (`validate`, `on_submit`, dll) — tapi TIDAK wajib migrasi semua sekaligus. `doc_events` tetap valid dipakai bareng `override_doctype_class`, dua-duanya jalan bareng tanpa konflik.

---

## 4. Alur Report Controller Override

**Masalah teknis:** `Report.execute_module()` (frappe/core/doctype/report/report.py:191-195) build path deterministik:
```python
method_name = get_report_module_dotted_path(module, self.name) + ".execute"
frappe.get_attr(method_name)(filters)
```
`get_report_module_dotted_path` cuma fungsi biasa di module yang sama — bisa di-monkeypatch di module-level, dan `execute_module` bakal otomatis pakai versi ter-patch karena Python resolve nama fungsi di call-time lewat namespace module.

**registry.py** (single source of truth, mirip gaya `override_doctype_class`):
```python
REPORT_OVERRIDES = {
    "Delivery Note Trends": "erpnext.gp_erp.report_controllers.delivery_note_trends",
}
```

**report_override.py** (patch minimal, ~10 baris, tidak sentuh behavior report yang tidak terdaftar):
```python
import frappe.core.doctype.report.report as report_module
from erpnext.gp_erp.report_controllers.registry import REPORT_OVERRIDES

_original = report_module.get_report_module_dotted_path

def _patched(module, report_name):
    return REPORT_OVERRIDES.get(report_name) or _original(module, report_name)

def apply():
    report_module.get_report_module_dotted_path = _patched
```

**delivery_note_trends.py** (signature harus sama persis kontrak Frappe — `execute(filters=None)` return `(columns, data)`):
```python
def execute(filters=None):
    from erpnext.stock.report.delivery_note_trends.delivery_note_trends import execute as original_execute
    columns, data = original_execute(filters)
    # custom logic tambahan
    return columns, data
```

**Entry point patch dipanggil:** satu baris di `erpnext/__init__.py` (file yang PASTI ke-import saat Frappe boot app, beda dengan `gp_erp/__init__.py` yang cuma ke-import lazy pas doctype-nya diakses):
```python
from erpnext.gp_erp.report_pacthing import report_override
report_override.apply()
```

---

## 5. Yang TIDAK dibuat sekarang (skip, sesuai fokus python)

- `public/js/controllers/` buat override JS — folder placeholder aja, isi nanti fase JS.
- JSON override — opsional/possible via Customize Form / custom field json (`gp_erp/custom/`), sudah ada mekanismenya, tidak butuh sistem baru.
- Registry abstraction buat DocType controller (tidak perlu, `hooks.py` dict udah cukup — native, satu file, tidak reinvent wheel).

---

## 6. Verifikasi

- DocType override: `bench --site test5 console` → `frappe.get_doc("Sales Invoice").__class__.__name__` harus `SalesInvoiceGP`.
- Report override: `bench --site test5 execute erpnext.gp_erp.report_pacthing.report_override.apply` lalu jalanin report dari UI, cek hasil ter-modifikasi.
- Assert self-check kecil ditinggal di `report_override.py` (misal `assert report_module.get_report_module_dotted_path is _patched` dipanggil sekali abis `apply()`).
