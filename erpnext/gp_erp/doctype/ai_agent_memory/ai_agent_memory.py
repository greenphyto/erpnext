# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate, flt
import json


class AIAgentMemory(Document):
    pass


def get_memory(ref_doctype, ref_name, company):
    """Get memory content for a reference entity.

    Args:
        ref_doctype: "Supplier" or "Customer"
        ref_name: Entity name (e.g. supplier name)
        company: Company name

    Returns:
        str: Markdown memory content, or empty string if not found
    """
    if not ref_doctype or not ref_name or not company:
        return ""

    name = frappe.db.get_value(
        "AI Agent Memory",
        {"reff_doctype": ref_doctype, "reff_name": ref_name, "company": company},
        "name"
    )
    if not name:
        return ""

    return frappe.db.get_value("AI Agent Memory", name, "memory") or ""


def create_memory(ref_doctype, ref_name, company, content):
    """Create a new memory record.

    Args:
        ref_doctype: "Supplier" or "Customer"
        ref_name: Entity name
        company: Company name
        content: Markdown content

    Returns:
        Document: Created AI Agent Memory doc
    """
    doc = frappe.new_doc("AI Agent Memory")
    doc.reff_doctype = ref_doctype
    doc.reff_name = ref_name
    doc.company = company
    doc.memory = content
    doc.updated_at = now_datetime()
    doc.insert(ignore_permissions=True)
    return doc


def update_memory(ref_doctype, ref_name, company, content):
    """Upsert memory record — update if exists, create if not.

    Args:
        ref_doctype: "Supplier" or "Customer"
        ref_name: Entity name
        company: Company name
        content: Markdown content

    Returns:
        Document: Updated or created AI Agent Memory doc
    """
    name = frappe.db.get_value(
        "AI Agent Memory",
        {"reff_doctype": ref_doctype, "reff_name": ref_name, "company": company},
        "name"
    )
    if name:
        doc = frappe.get_doc("AI Agent Memory", name)
        doc.memory = content
        doc.updated_at = now_datetime()
        doc.save(ignore_permissions=True)
    else:
        doc = create_memory(ref_doctype, ref_name, company, content)
    return doc


def update_memory_on_submit(doc, method=""):
    """Auto-update memory when Purchase Invoice is submitted.

    Hooked to Purchase Invoice.on_submit.
    Error logged but does NOT block PI submit.
    """
    if not doc.supplier or not doc.company:
        return
    try:
        update_memory_from_pi(doc.name)
    except Exception as e:
        frappe.log_error(
            f"AI Agent Memory update failed for {doc.name}: {e}",
            "AI Agent Memory"
        )


@frappe.whitelist()
def update_memory_from_pi(pi_name):
    """Manually regenerate memory from a specific Purchase Invoice.

    Args:
        pi_name: Purchase Invoice name

    Returns:
        Document: Updated AI Agent Memory doc
    """
    pi_doc = frappe.get_doc("Purchase Invoice", pi_name)
    if not pi_doc.supplier or not pi_doc.company:
        frappe.throw("Supplier and Company are required")

    # Fetch scanned names from email_invoice data_result
    scanned_map = _get_scanned_names(pi_doc)

    memory_content = _generate_memory_from_pi(pi_doc, scanned_map)
    return update_memory("Supplier", pi_doc.supplier, pi_doc.company, memory_content)


def _get_scanned_names(pi_doc):
    """Fetch scanned item names from Email Invoice data_result.

    Matches by bill_no + bill_date to find the originating Email Invoice,
    then extracts scanned item names from the JSON result.

    Returns:
        dict: {index: scanned_name} mapping
    """
    if not pi_doc.bill_no or not pi_doc.bill_date:
        return {}

    # Find Email Invoice result linked to this PI
    result = frappe.db.get_value(
        "Email Invoice Result",
        {"invoice_no": pi_doc.name},
        "parent",
    )
    if not result:
        # Try matching by invoice_no on Email Invoice
        ei_name = frappe.db.get_value(
            "Email Invoice",
            {"invoice_no": pi_doc.name},
            "name"
        )
        if not ei_name:
            return {}
        data_result = frappe.db.get_value("Email Invoice", ei_name, "data_result")
    else:
        ei_name = result
        data_result = frappe.db.get_value("Email Invoice", ei_name, "data_result")

    if not data_result:
        return {}

    try:
        payloads = json.loads(data_result) if isinstance(data_result, str) else data_result
    except (json.JSONDecodeError, TypeError):
        return {}

    if not isinstance(payloads, list):
        payloads = [payloads]

    scanned_map = {}
    idx = 0
    for payload in payloads:
        res = payload.get("result") or payload
        if "result" in res:
            res = res.get("result")
        items = res.get("items") or []
        for item in items:
            name = item.get("name") or item.get("item_name") or ""
            if name:
                scanned_map[idx] = name
            idx += 1

    return scanned_map


def _generate_memory_from_pi(pi_doc, scanned_map=None):
    """Generate markdown memory content from a submitted Purchase Invoice.

    Args:
        pi_doc: Purchase Invoice document
        scanned_map: dict {index: scanned_name} from OCR

    Returns:
        str: Markdown content
    """
    scanned_map = scanned_map or {}

    # Items table
    items_lines = "| Scanned Name | Item Name | UOM | Cost Center | Expense Head | Avg Rate |"
    items_lines += "\n|--------------|-----------|-----|-------------|--------------|----------|"
    for idx, item in enumerate(pi_doc.items):
        scanned = scanned_map.get(idx, "-")
        item_name = item.item_name or item.item_code or "-"
        uom = item.uom or "-"
        cost_center = _clean_html(item.cost_center or "-")
        expense_head = _clean_html(item.expense_account or "-")
        rate = flt(item.rate, 2) if item.rate else "-"
        items_lines += f"\n| {scanned} | {item_name} | {uom} | {cost_center} | {expense_head} | {rate} |"

    # Invoice pattern
    currency = pi_doc.currency or "-"
    payment_terms = pi_doc.payment_terms_template or "-"

    # Addresses — clean HTML tags, replace <br> with comma
    shipping = _clean_address(getattr(pi_doc, 'shipping_address_display', None) or getattr(pi_doc, 'shipping_address', None))
    billing = _clean_address(getattr(pi_doc, 'billing_address_display', None) or getattr(pi_doc, 'billing_address', None))

    # Tax template and details
    tax_template = _clean_html(pi_doc.taxes_and_charges or "-")
    tax_details = []
    for t in (pi_doc.taxes or []):
        tax_details.append(f"- {_clean_html(t.description)}: {t.rate}% ({t.charge_type})")

    tax_section = f"- Tax Template: {tax_template}"
    if tax_details:
        tax_section += "\n" + "\n".join(tax_details)

    markdown = f"""# {pi_doc.supplier}

## Items
{items_lines}

## Invoice Pattern
- Currency: {currency}
- Payment Terms: {payment_terms}

## Addresses
- Shipping: {shipping}
- Billing: {billing}

## Tax & Accounts
{tax_section}
"""
    return markdown.strip()


def _clean_html(text):
    """Remove HTML tags and decode entities from text."""
    if not text:
        return "-"
    import html
    import re
    text = html.unescape(str(text))
    text = re.sub(r'<br\s*/?>', ', ', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip() or "-"


def _clean_address(text):
    """Clean address HTML: replace <br> with ' | ', remove other tags."""
    if not text:
        return "-"
    import html
    import re
    text = html.unescape(str(text))
    text = re.sub(r'<br\s*/?>', ' | ', text)
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up multiple spaces and leading/trailing separators
    text = re.sub(r'\s+', ' ', text)
    text = text.strip().strip('|').strip()
    return text or "-"
