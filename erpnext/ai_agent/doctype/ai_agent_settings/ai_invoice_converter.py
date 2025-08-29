from typing import Optional

import requests

import frappe
from frappe.utils import cstr

class AIAgentClient:
    """
    Simple controller to interact with an AI Invoice converter REST API.

    - Reads `server_url` from `AI Agent Settings` doctype when not provided.
    - Uploads a local invoice file as multipart form to `/extract-text`.
    - Returns extracted text when available (falls back to raw response text).
    """
    def __init__(self, server_url: Optional[str] = None, timeout: int = 300):
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
        email: str,
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

        text = cstr(data.get("text")) + f"\nemail: {email}"
        if isinstance(text, str):
            self.text = text
        else:
            self.text = resp.text

        return self.text

    def get_invoice_data(self, text: str):
        """
        Call `/get_invoice_data` with extracted OCR text and a supplier reference.

        Args:
            text: OCR text content.
        Returns:
            Parsed JSON response (dict) resembling sample_data.json structure.
        """

        url = self._join_url("/get-invoice-data")
        payload = {"text": text or ""}
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()

        try:
            return resp.json()
        except ValueError:
            # If server didn't return JSON, wrap as best-effort structure
            return {"text": text or "", "raw": resp.text}

    def extract_invoice(self, invoice_path: str, reference: str, email: str, lang: Optional[str] = None):
        """
        Convenience: OCR the invoice file, then fetch structured invoice data.

        - Step 1: `/extract-text` with multipart upload -> text
        - Step 2: `/get-invoice-data` with text + reference

        Returns parsed invoice data dict.
        """
        text = self.extract_text(invoice_path, email, lang=lang)
        return self.get_invoice_data(text=text)

    def get_supplier(self, payload):
        """
        Get supplier match from Company name or Domains
        Body = {
            "supplier_names":["HTP Co., Ltd"],
            "domains":["iplusmobot.com"],
            "references":{"Iplusmobot":{"keyword":"Hangzhou Iplusmobot Technology Co., Ltd","emails":[]},"Bio-Flora SG":{"keyword":"Bio-Flora(Singapore) Pte Ltd","emails":[]}},
            "domain_map:":{"iplusmobot.com":["Iplusmobot","Hangzhou Iplusmobot Technology Co., Ltd"],"bioflora.com.sg":["Bio-Flora SG","Bio-Flora(Singapore) Pte Ltd"]}
        }
        """
        url = self._join_url("/get-supplier")
        resp = requests.post(url, json=payload)

        resp.raise_for_status()

        try:
            return resp.json()
        except ValueError:
            # If server didn't return JSON, wrap as best-effort structure
            return {
                "code":None
            }