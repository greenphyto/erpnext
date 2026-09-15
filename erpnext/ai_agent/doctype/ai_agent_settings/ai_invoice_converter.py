from typing import Optional

import requests

import frappe, json, re
from frappe.utils import cstr, cint

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

    def extract_text_old(
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

        text = cstr(data.get("text")) + f"\nSender: {email}"
        if isinstance(text, str):
            self.text = text
        else:
            self.text = resp.text

        return self.text
    
    def extract_text(
        self,
        invoice_path: str,
        email: str,
        lang: Optional[str] = None,
    ):
        return self.extract_text_via_google_vision(invoice_path, email, lang=lang)

    def extract_text_via_google_vision(
        self,
        invoice_path: str,
        email: str,
        lang: Optional[str] = None,
    ):
        """
        Alternative: extract text using Google Vision API directly (no AI server needed).

        Supports both images and PDFs (via pdf2image).
        Requires `google_vision_api_key` in site config.
        """
        from erpnext.controllers.google_vision import extarct_text_from_file

        text = extarct_text_from_file(invoice_path)
        if not text:
            text = ""

        text += f"\nSender: {email}"
        self.text = text
        return self.text

    def get_invoice_data(self, text: str, supplier_default:str):
        """
        Call `/get_invoice_data` with extracted OCR text and a supplier reference.

        Args:
            text: OCR text content.
        Returns:
            Parsed JSON response (dict) resembling sample_data.json structure.
        """

        url = self._join_url("/get-invoice-data")
        payload = {"text": text[:2000] or "", "supplier_default":supplier_default}
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()

        try:
            return resp.json()
        except ValueError:
            # If server didn't return JSON, wrap as best-effort structure
            return {"text": text or "", "raw": resp.text}

    def extract_invoice(self, invoice_path: str, references: list, email: str, lang: Optional[str] = None):
        """
        Convenience: OCR the invoice file, then fetch structured invoice data.

        - Step 1: `/extract-text` with multipart upload -> text
        - Step 2: `/get-invoice-data` with text + reference

        Returns parsed invoice data dict.
        """
        text = self.extract_text(invoice_path, email, lang=lang) or ""

        # check continue or not
        if not self.validate_text(text):
            return {
                "error":"Attachment is not invoice"
            }
        
        supplier_default = self.get_supplier_default(text, email, references)

        return self.get_invoice_data(text=text, supplier_default=supplier_default)
    
    def get_supplier_default(self, text, emails, supplier_references):
        # or by looking for domain
        if emails:
            supplier = frappe.db.get_value("Supplier", {"website":['in', emails]})
            if supplier:
                return supplier
        
        payload = {
            "text":text,
            "supplier_data": json.loads(supplier_references)
        }
        url = self._join_url("/get-supplier-from-text")
        resp = requests.post(url, json=payload)

        resp.raise_for_status()

        try:
            data = resp.json() or {}
            data = data.get("exact_hits")
            if data:
                keys = list(data.keys())
                if keys:
                    return keys[0]
                
        except ValueError:
            return ""

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
        threshold = cint(frappe.db.get_single_value("Buying Settings", "supplier_threshold"))
        url = self._join_url("/get-supplier")
        payload['threshold'] = threshold
        resp = requests.post(url, json=payload)

        resp.raise_for_status()

        try:
            return resp.json()
        except ValueError:
            # If server didn't return JSON, wrap as best-effort structure
            return {
                "code":None
            }
    
    def get_supplier_domain(self, supplier_list):
        url = self._join_url("/get-supplier-domain")
        payload = {"supplier_list":supplier_list}
        resp = requests.post(url, json=payload)

        resp.raise_for_status()

        try:
            return resp.json()
        except ValueError:
            # If server didn't return JSON, wrap as best-effort structure
            return {
                "result":[]
            }

    def validate_text(self, text):
        from erpnext.controllers.ai import chat_completion

        # AI-based validation
        SYSTEM_PROMPT = """
You are a document classifier. Your task is to determine whether the given OCR-extracted text is an invoice or not.

An invoice is a document whose sole and primary purpose is to request payment from a recipient for goods or services rendered. It typically contains some combination of the following:
- A specific amount due or balance due
- Line items, quantities, or pricing for goods or services
- Payment instructions, bank details, or account information
- Tax amounts such as GST or VAT
- An invoice number or reference tied to a financial transaction

If the primary purpose of the document is anything other than requesting payment, it is NOT an invoice. This includes but is not limited to letters, notices, certificates, legal documents, regulatory communications, administrative documents, reports, contracts, or any other document that merely mentions money, a reference number, or a financial context as a secondary detail.

Ask yourself one question: is the main reason this document exists to bill someone for payment? If no, return false.

Return ONLY a valid JSON object with no explanation, no markdown, no preamble:
{"result": true}
or
{"result": false}
"""
        result = chat_completion(SYSTEM_PROMPT, text)
        if not result:
            return True  # fallback: treat as invoice if AI fails

        try:
            data = json.loads(result)
            return data.get("result", True)
        except (json.JSONDecodeError, TypeError):
            return True