import frappe
from frappe.model import naming
from frappe.model.naming import NamingSeries, getseries, has_custom_parser, determine_consecutive_week_number
from frappe.model.naming import NAMING_SERIES_PART_TYPES
from frappe.utils import cstr
from frappe.utils.data import now_datetime, get_datetime

_DATE_PARTS = {"YY", "YYYY", "MM", "DD", "WW", "timestamp"}

_original_generate_next_name = NamingSeries.generate_next_name


def _no_reset_enabled(doctype):
    if not doctype:
        return False
    try:
        return bool(frappe.get_cached_value("DocType", doctype, "no_reset_number"))
    except Exception:
        return False


def _parse_naming_series_no_reset(parts, doc=None):
    if isinstance(parts, str):
        parts = parts.split(".")

    name = ""
    _sentinel = object()
    series_set = False
    today = now_datetime()

    if doc:
        use_date = doc.get("transaction_date") or doc.get("posting_date") or doc.get("creation")
        if use_date:
            today = get_datetime(use_date)

    key_series = []
    for e in parts:
        if not e:
            continue

        part = ""
        if e.startswith("#"):
            if not series_set:
                temp = ".".join(key_series)
                part = getseries(temp, len(e))
                series_set = True
        elif e == "YY":
            part = today.strftime("%y")
        elif e == "MM":
            part = today.strftime("%m")
        elif e == "DD":
            part = today.strftime("%d")
        elif e == "YYYY":
            part = today.strftime("%Y")
        elif e == "WW":
            part = determine_consecutive_week_number(today)
        elif e == "timestamp":
            part = str(today)
        elif doc and (e.startswith("{") or doc.get(e, _sentinel) is not _sentinel):
            e = e.replace("{", "").replace("}", "")
            part = doc.get(e)
            key_series.append(part)
        elif method := has_custom_parser(e):
            part = frappe.get_attr(method[0])(doc, e)
        else:
            part = e
            key_series.append(part)

        if isinstance(part, str):
            name += part
        elif isinstance(part, NAMING_SERIES_PART_TYPES):
            name += cstr(part).strip()

    return name


def _generate_next_name(self, doc, *, ignore_validate=False):
    doctype = doc.doctype if doc is not None else None
    if _no_reset_enabled(doctype):
        if not ignore_validate:
            self.validate()
        parts = self.series.split(".")
        return _parse_naming_series_no_reset(parts, doc=doc)
    return _original_generate_next_name(self, doc, ignore_validate=ignore_validate)


def apply():
    if getattr(NamingSeries.generate_next_name, "_erpnext_no_reset_patched", False):
        return
    _generate_next_name._erpnext_no_reset_patched = True
    NamingSeries.generate_next_name = _generate_next_name
