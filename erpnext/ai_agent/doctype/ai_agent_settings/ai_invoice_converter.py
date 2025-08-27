import base64
from typing import Optional

import requests

try:
    import frappe
except Exception:  # pragma: no cover - allows use outside Frappe context for linting
    frappe = None  # type: ignore

class AIInvoiceConverterController:
    """
    Simple controller to interact with an AI Invoice converter REST API.

    - Reads `server_url` from `AI Agent Settings` doctype when not provided.
    - Encodes a local invoice file as base64 and posts it to `/extract_text`.
    - Returns extracted text when available (falls back to raw response text).
    """

    def __init__(self, server_url: Optional[str] = None, timeout: int = 60):
        self.timeout = timeout
        self.server_url = server_url or self._get_server_url_from_settings()
        if not self.server_url:
            raise ValueError("AI Invoice Converter server_url is not configured")

    def _get_server_url_from_settings(self) -> Optional[str]:
        if frappe is None:
            return None
        # Prefer lightweight single value fetch
        url = frappe.db.get_single_value("AI Agent Settings", "server_url")
        if not url:
            try:
                # Fallback to full document in case of caching/issues
                doc = frappe.get_single("AI Agent Settings")
                url = getattr(doc, "server_url", None)
            except Exception:
                url = None
        return url

    def _join_url(self, path: str) -> str:
        base = (self.server_url or "").rstrip("/")
        path = path if path.startswith("/") else f"/{path}"
        return f"{base}{path}"

    def extract_text(self, invoice_path: str, as_form: bool = False, return_meta: bool = False):
        """
        Read a local invoice file, encode as base64, and send to `/extract_text`.

        Args:
            invoice_path: Path to the invoice file on disk.
            as_form: Send payload as form fields instead of JSON.
            return_meta: When True, return the full JSON {"text","chars"}.

        Returns:
            By default a string of extracted text. If `return_meta=True`, returns
            a dict with keys {"text": str, "chars": int}.
        """
        if not invoice_path:
            raise ValueError("invoice_path must be provided")

        with open(invoice_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        url = self._join_url("/extract_text")
        payload = {"invoice_base64": encoded}

        if as_form:
            resp = requests.post(url, data=payload, timeout=self.timeout)
        else:
            resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()

        # Expect JSON: {"text": str, "chars": int}
        try:
            data = resp.json()
        except ValueError:
            return resp.text if not return_meta else {"text": resp.text, "chars": len(resp.text)}

        if not isinstance(data, dict):
            return resp.text if not return_meta else {"text": resp.text, "chars": len(resp.text)}

        text = data.get("text")
        chars = data.get("chars")

        if return_meta:
            if text is None and isinstance(chars, int):
                body = resp.text
                return {"text": body, "chars": len(body)}
            if text is not None and not isinstance(chars, int):
                return {"text": text, "chars": len(text)}
            return {"text": text or "", "chars": chars if isinstance(chars, int) else len(text or "")}

        if isinstance(text, str):
            return text
        return resp.text

    def get_invoice_data(self, text: str, reference: Optional[str] = None, as_form: bool = False):
        """
        Call `/get_invoice_data` with extracted OCR text and a supplier reference.

        Args:
            text: OCR text content.
            reference: Supplier reference string. If None, tries to read via `get_supplier_context()`.
            as_form: Send payload as form fields instead of JSON.

        Returns:
            Parsed JSON response (dict) resembling sample_data.json structure.
        """
        if reference is None:
            # Import lazily to avoid import errors when used outside ERPNext runtime
            try:
                from erpnext.controllers.erp import get_supplier_context  # type: ignore
                reference = get_supplier_context()
            except Exception:
                reference = ""

        url = self._join_url("/get_invoice_data")
        payload = {"text": text or "", "reference": reference or ""}

        if as_form:
            resp = requests.post(url, data=payload, timeout=self.timeout)
        else:
            resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()

        try:
            return resp.json()
        except ValueError:
            # If server didn't return JSON, wrap as best-effort structure
            return {"text": text or "", "reference": reference or "", "raw": resp.text}

    def extract_invoice(self, invoice_path: str, reference: Optional[str] = None, as_form: bool = False):
        """
        Convenience: OCR the invoice file, then fetch structured invoice data.

        - Step 1: `/extract_text` with base64 file -> text
        - Step 2: `/get_invoice_data` with text + reference

        Returns parsed invoice data dict.
        """
        text = self.extract_text(invoice_path, as_form=as_form, return_meta=False)
        return self.get_invoice_data(text=text, reference=reference, as_form=as_form)
