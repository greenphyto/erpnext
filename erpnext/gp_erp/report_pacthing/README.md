# report_pacthing/

Small infrastructure that patches `get_report_module_dotted_path`
(`frappe/core/doctype/report/report.py`) so Frappe redirects execution of
selected existing reports to `gp_erp/report_controllers/`.

This exists only because Frappe has no native hook for overriding a
report's dotted module path (unlike `override_doctype_class` for
DocTypes). See `gp_erp/OVERIDE_PLAN_v14.md` section 1 for the "native
hook vs monkey-patch" rationale.

## How to use

This folder is infra-only — you should not need to touch it when adding
a new report override. To add an override, edit
`gp_erp/report_controllers/registry.py` instead.

`report_override.py` (not yet created) will look like:

```python
import frappe.core.doctype.report.report as report_module
from erpnext.gp_erp.report_controllers.registry import REPORT_OVERRIDES

_original = report_module.get_report_module_dotted_path

def _patched(module, report_name):
    return REPORT_OVERRIDES.get(report_name) or _original(module, report_name)

def apply():
    report_module.get_report_module_dotted_path = _patched
    assert report_module.get_report_module_dotted_path is _patched
```

Applied once at boot, from `erpnext/__init__.py` (not `gp_erp/__init__.py`,
which is only imported lazily when a `gp_erp` doctype is accessed):

```python
from erpnext.gp_erp.report_pacthing import report_override
report_override.apply()
```

## Rules

- Do not modify `report.py` in Frappe core directly — this folder is the
  only patch point.
- Keep the patch function minimal: fall back to `_original` for any
  report not in `REPORT_OVERRIDES`.
- One `apply()` call at boot, nowhere else.

## Planned implementation

Empty for now. Not yet implemented:

- `report_override.py` — the patch itself (~10 lines, shown above).
- Wiring in `erpnext/__init__.py` to call `report_override.apply()`.

Verification once implemented:
`bench --site test5 execute erpnext.gp_erp.report_pacthing.report_override.apply`
