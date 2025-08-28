from typing import Optional

import requests

try:
    import frappe
except Exception:  # pragma: no cover - allows use outside Frappe context for linting
    frappe = None  # type: ignore

class AIAgentClient:
    """
    Simple controller to interact with an AI Invoice converter REST API.

    - Reads `server_url` from `AI Agent Settings` doctype when not provided.
    - Uploads a local invoice file as multipart form to `/extract-text`.
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

    def extract_text(
        self,
        invoice_path: str,
        lang: Optional[str] = None,
    ):
        """
        Read a local invoice file and send to `/extract-text` as multipart form.

        Args:
            invoice_path: Path to the invoice file on disk.
            lang: Optional language hint forwarded as a form field `lang`.

        Returns:
            A string of extracted text.
        """
        if not invoice_path:
            raise ValueError("invoice_path must be provided")

        url = self._join_url("/extract-text")

        # Always send as multipart form: files=<UploadFile>, lang=<Optional[str]>
        import os

        with open(invoice_path, "rb") as fh:
            filename = os.path.basename(invoice_path) or "invoice"
            files = {"files": (filename, fh, "application/octet-stream")}
            data = {"lang": lang} if lang else None
            resp = requests.post(url, files=files, data=data, timeout=self.timeout)
            
        resp.raise_for_status()

        # Expect JSON: {"text": str, "chars": int}
        try:
            data = resp.json()
        except ValueError:
            return resp.text

        if not isinstance(data, dict):
            return resp.text

        text = data.get("text")
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

        url = self._join_url("/get-invoice-data")
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
        text = self.extract_text(invoice_path)
        return self.get_invoice_data(text=text, reference=reference, as_form=as_form)
