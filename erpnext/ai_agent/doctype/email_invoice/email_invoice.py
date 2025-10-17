# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
from frappe.utils import flt, getdate, get_time
from erpnext.controllers.erp import get_supplier_context, is_doctype_exists, deep_get, get_supplier_payload
import os, re
from frappe.utils import get_traceback, cstr
from erpnext.ai_agent.doctype.ai_agent_settings.ai_invoice_converter import AIAgentClient
from six import string_types

MAX_DISPLAY_LENGTH = 300
SHORT_HEAD = 300
SHORT_TAIL = 700
GST_DEFAULT = 9
class EmailInvoice(Document):
	def validate(self):
		self.set_status()

	# --- Reason helpers ---
	def _init_reasons(self):
		if not hasattr(self, "_reasons"):
			self._reasons = []
		return self._reasons

	def add_reason(self, category, message="", code="", context=None):
		"""Collect categorized reasons during processing.

		- category: high-level bucket (e.g., attachment, pdf, agent, po, system)
		- code: short machine-friendly string (e.g., no_attachment, not_pdf)
		- message: brief human-friendly description
		- context: optional dict with extra info (file name, path tail, etc.)
		"""
		reasons = self._init_reasons()
		entry = {"category": category}
		if code:
			entry["code"] = code
		if message:
			entry["message"] = message
		if context:
			entry["context"] = context
		reasons.append(entry)

	def _finalize_reasons(self):
		"""Store aggregated reasons and set short selectable reason."""
		reasons = getattr(self, "_reasons", [])
		if not reasons:
			return
		# Store JSON to unknown_reason for detail
		try:
			import json as _json
			payload = {"reasons": reasons}
			text = _json.dumps(payload)
			self.error_trace = text
		except Exception:
			pass
		# Also add compact summary for quick debugging
		cats = [
			f"{(r.get('category') or '').strip()}:{(r.get('code') or '').strip()}".strip(":")
			for r in reasons
			if isinstance(r, dict)
		]
		self.system_reason = "; ".join(c for c in cats if c)[:1000]
		# Calculate and set short reason used for list filtering
		self.reason = self._compute_short_reason(reasons)

	def _compute_short_reason(self, reasons):
		"""Map collected detailed reasons to short, selectable reason.

		Priority:
		- System Error
		- PI… (Missing Data / Unknown Item / Empty Items / Multi Currency / Create Failed)
		- PDF… (Encrypted / Failed)
		- Attachment… (Not PDF / File Missing / No Attachment)
		- Agent No Result
		- Unknown
		"""
		# Normalize for scanning
		def has(cat, code=None):
			for r in reasons:
				if not isinstance(r, dict):
					continue
				if r.get("category") == cat and (code is None or r.get("code") == code):
					return r
			return None

		# 1) System errors
		if has("system", "exception"):
			return "System Error"

		# 2) PI creation problems (inspect message for specifics)
		pi = has("pi", "create_failed")
		if pi:
			msg = (pi.get("message") or "").lower()
			if "missing data" in msg:
				return "PI Missing Data"
			if "cannot recognise item" in msg or "cannot recognize item" in msg or "unknown item" in msg:
				return "PI Unknown Item"
			if "item is empty" in msg or "items is empty" in msg or "item empty" in msg:
				return "PI Empty Items"
			if "multiple currency" in msg:
				return "PI Multi Currency"
			return "PI Create Failed"

		# 3) PDF issues
		if has("pdf", "encrypted_pdf"):
			return "PDF Encrypted"
		if has("pdf", "pdf_conversion_failed"):
			return "PDF Failed"

		# 4) Attachment issues
		if has("attachment", "not_pdf"):
			return "Not PDF"
		if has("attachment", "missing_file"):
			return "File Missing"
		if has("attachment", "no_attachment"):
			return "No Attachment"

		# 5) Agent
		if has("agent", "no_extraction_result"):
			return "Agent No Result"

		return "Unknown"

	def set_status(self):
		if self.invoice_no:
			self.reason = ""
			self.error_trace = ""
			self.status = "Matched"
		elif self.po_no:
			self.status = "Pending"
		else:
			self.status = "Unknown"

	def sync_email(self, comm_name="", doc=None):
		if not doc:
			doc = frappe.get_doc("Communication", comm_name)
		self.sender = doc.sender
		self.cc = doc.cc
		self.bcc = doc.bcc
		content = ""
		if len(doc.content or "") > MAX_DISPLAY_LENGTH:
			content = (
				(doc.content or "")[:SHORT_HEAD]
				+ "<br><br><--- Message hidden because too long ---><br><br>"
				+ (doc.content or "")[-SHORT_TAIL:]
			)
		else:
			content = doc.content or ""

		self.message = content
		self.received_date = getdate(doc.communication_date)
		self.time = get_time(doc.communication_date)
		self.subject = doc.subject
		self.message_id = doc.message_id
		self.inbox = doc.name
		self.process_email(doc)

	@frappe.whitelist()
	def sync_from_ui(self):
		if self.data_result:
			for d in json.loads(self.data_result) or []:
				payload = self.enhance_payload(payload)
				self.create_invoice_result(payload)
		else:
			self.process_email()
		
		self.save()

	def process_email(self, doc={}):
		"""Process email using AIAgentClient end-to-end extraction and PI creation.

		- Mirrors logic in `process_email` for attachment checks and reason handling.
		- Uses `AIAgentClient.extract_invoice(path, reference)` to obtain structured JSON.
		- Persists extracted JSON (including fallback with raw text) to `data_result`.
		- Creates Non-stock Purchase Invoice via `create_purchase_invoice_non_stock`.
		"""
		self._init_reasons()
		if not doc and self.inbox:
			doc = frappe.get_doc("Communication", self.inbox)

		# Collect attachments linked to this email
		file_doc_name = frappe.db.get_list(
			"File",
			{"attached_to_doctype": "Communication", "attached_to_name": doc.name},
		)

		# No attachments at all
		if not file_doc_name:
			self.add_reason(
				category="attachment",
				code="no_attachment",
				message="No attachments found on the email",
			)
			self._finalize_reasons()
			return

		# Prepare agent and context
		supp_context = get_supplier_context()
		results_payload = []
		pi_created = []
		agent_exc = None
		try:
			agent = AIAgentClient()
		except Exception as e:
			agent = None
			agent_exc = e

		self.results = []
		for file_name in file_doc_name:
			fn = frappe.get_doc("File", file_name.get("name"))
			full_path = fn.get_full_path()

			# Check file exists
			if not os.path.exists(full_path):
				self.add_reason(
					category="attachment",
					code="missing_file",
					message="Attached file not found on server",
					context={"file": fn.file_name, "url": fn.file_url},
				)
				continue

			# Copy attachment to current EmailInvoice for traceability
			if not frappe.db.get_list(
				"File",
				{"attached_to_doctype": "Email Invoice", 
	 			"attached_to_name": self.name, "file_name": fn.file_name},
			):
				self.add_attachment_copy(fn)

			# Only handle PDFs (consistent with process_email)
			if ".pdf" not in full_path.lower():
				self.add_reason(
					category="attachment",
					code="not_pdf",
					message="Attachment is not a PDF",
					context={"file": fn.file_name},
				)
				continue

			# Try basic open to detect encryption/invalid PDF (for reason classification)
			ok, img_or_msg = convert_pdf_to_img(full_path)
			if not ok:
				msg = img_or_msg or "PDF conversion failed"
				code = "encrypted_pdf" if "encrypted" in (msg or "").lower() else "pdf_conversion_failed"
				self.add_reason(
					category="pdf",
					code=code,
					message=str(msg)[:200],
					context={"file": fn.file_name},
				)
				continue

			# If agent couldn't be constructed, record and skip further processing
			if not agent:
				self.add_reason(
					category="system",
					code="exception",
					message=f"AI Agent init failed: {agent_exc}",
					context={"file": fn.file_name},
				)
				continue

			# Extract structured data via agent; handle fallback JSON
			extracted = None
			sender = self.get_sender_domain()
			try:
				extracted = agent.extract_invoice(full_path, references=supp_context, email=sender)
			except Exception as e:
				# Record system exception; no structured fallback available here
				self.add_reason(
					category="system",
					code="exception",
					message=f"{e}",
					context={"file": fn.file_name},
				)
				continue

			# If nothing meaningful returned, keep reason and continue
			if not extracted:
				self.add_reason(
					category="agent",
					code="no_extraction_result",
					message="AI agent returned no result",
					context={"file": fn.file_name},
				)
				continue

			# Keep copy of extracted JSON for audit and later review
			# Also include `file` so downstream creation can attach it
			payload = {"result": extracted, "file": fn.name}
			# Duplicate on root to simplify consumers that expect flat structure
			payload.update({"document": extracted.get("document") if isinstance(extracted, dict) else None})
			results_payload.append(payload)

			# Enhance the result
			payload = self.enhance_payload(payload)

			# Attempt to create Non-stock PI from this extracted data
			r, name = self.create_invoice_result(payload)
			if not r:
				self.add_reason(
					category="pi",
					code="create_failed",
					message=str(name),
					context={"file": fn.file_name},
				)
				continue

			try:
				if doc:
					# Link communication to created PI and remember
					row = self.append("results")
					row.filename = fn.file_name
					row.po_no = self.flags.po_no
					row.invoice_no = name
					row.insert()
					
					# copy attachment
					self.add_attachment_copy(fn, "Purchase Invoice", name )
				if not self.invoice_no:
					self.invoice_no = name
			except Exception:
				pass
			pi_created.append(name)

		# Persist extracted data (including raw fallback if any) for all processed files
		try:
			self.data_result = json.dumps(results_payload)
		except Exception:
			# As last resort, store repr
			try:
				self.data_result = repr(results_payload)
			except Exception:
				pass

		# Finalize reasons only if nothing created; set status accordingly
		if not pi_created:
			self._finalize_reasons()
		self.set_status()
		return pi_created

	def get_sender_domain(self):
		# exclude from home domain
		conf = frappe.local.conf
		exclude_list = [conf.invoice_email, conf.hostname] + conf.email_whitelist
		exclude_list = extract_domains(exclude_list)

		# extract from email content
		doc = frappe.get_doc("Communication", self.inbox)
		text = doc.content
		pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
		emails = re.findall(pattern, text)
		unique_emails = sorted(set(email.lower() for email in emails))
		domains = sorted(
				set(
					email.split('@')[1].lower()
					for email in unique_emails
					if "@" in email and email.split('@')[1].lower() not in exclude_list
				)
			)
		return domains

	def enhance_payload(self, payload):
		# update supplier
		# update item, soon
		
		supplier = []
		domains = []
		result = payload['result']
		if 'result' in result:
			result = result.get("result")
		
		# Supplier
		supp = deep_get(result, ['supplier', 'name'], "")
		if not frappe.db.exists('Supplier', supp):
			supplier.append(supp)
			website = deep_get(result, ['supplier', 'contacts', 'website'] )
			if website:
				self.update_website(supp, website)
				
			email = deep_get(result, ['supplier', 'contacts', 'email'] )
			domains += [website, email]

			agent = AIAgentClient()
			supp_payload = get_supplier_payload(supplier, domains)
			temp = agent.get_supplier(supp_payload)
			supplier_final = temp.get("code")
			if supplier_final:
				payload['result']['result']['supplier']['name'] = supplier_final
		
		# PO Number
		def normalize_po(text: str) -> str:
			if not text:
				return None
			s = text.upper().strip()
			replacements = {
				"O": "0",
				"Q": "0",
				"I": "1",
				"L": "1",
				"S": "5",
				"B": "8"
			}
			for k, v in replacements.items():
				s = s.replace(k, v)

			if not s.startswith("PO"):
				s = "PO" + s.lstrip("P0OQ")  # buang prefix mirip lalu pakai PO

			match = re.search(r"PO(\d{1,6})/(\d{4})", s)
			if match:
				number = match.group(1).zfill(6)  # padding ke 6 digit
				year = match.group(2)
				return f"PO{number}/{year}"
			return None
		po_number = deep_get(result, ['document', 'references', 'purchase_order_number'] )
		payload['result']['result']['document']['references']['purchase_order_number'] = normalize_po(po_number) or po_number
			
		return payload
	
	def update_website(self, supplier, website):
		if not frappe.get_value("Supplier", supplier, 'website'):
			frappe.db.set_value("Supplier", supplier, 'website', website)

	def create_invoice_result(self, result=[], com_doc=""):
		"""Create a Purchase Invoice based on extracted payload.

		Behavior:
		- If payload indicates a Purchase Order reference (purchase_order_number), create PI from PO and update rates using JSON values.
		- Otherwise, create a Non-stock PI using `create_purchase_invoice_non_stock`.

		Returns (bool, name_or_error): compatible with `process_email` expectations.
		"""
		if not com_doc and self.inbox:
			com_doc = frappe.get_doc("Communication", self.inbox)

		# Normalize input: allow dict (single), list (multiple), or fallback to saved data_result
		if isinstance(result, string_types):
			result = json.loads(result)
		
		payloads = []
		if isinstance(result, dict):
			payloads.append(result)
		else:
			payloads = result

		last_ok = False
		last_name = ""
		for res in payloads:
			name = None
			try:
				res = res.get("result") or res
				if 'result' in res:
					res = res.get("result")

				# Try to detect PO reference from common locations
				po_ref = deep_get(res, ["document","references","purchase_order_number"], "")
				# check exists
				po_ref = frappe.db.exists("Purchase Order", {"name":po_ref})
				if po_ref:
					self.flags.po_no = po_ref
					ok, name_or_err = self.create_invoice(res, po_ref=po_ref)
					if not ok:
						self.add_reason(category="pi", code="create_failed", message=str(name_or_err))
						return False, name_or_err
					name = name_or_err
				else:
					ok, name_or_err = self.create_purchase_invoice_non_stock(res)
					if not ok:
						self.add_reason(category="pi", code="create_failed", message=str(name_or_err))
						return False, name_or_err
					name = name_or_err

			except Exception as e:
				name = ""
				self.add_reason(category="system", code="exception", message=f"{e}")
				self.error_trace = get_traceback()
				return False, str(e)

			# Link communication only for the last created doc in the batch
			if name and com_doc:
				try:
					com_doc.db_set("reference_doctype", "Purchase Invoice")
					com_doc.db_set("reference_name", name)
					if not self.invoice_no:
						self.invoice_no = name
				except Exception:
					pass
			last_ok = True
			last_name = name

		# Update status/reasons if nothing created
		if not last_ok:
			self._finalize_reasons()
		self.set_status()
		return last_ok, last_name

	def create_invoice(self, data=None, po_ref=None):
		"""Create Purchase Invoice from an existing Purchase Order and update item rates.

		- Detects the Purchase Order number from `data` (supports nested result structure).
		- Builds PI via `make_purchase_invoice(PO)`.
		- Updates item rates from JSON result (latest price) without altering PO quantities.
		- Mentions rate changes via a Comment on the created document.
		"""
		if not data:
			return False, "Missing data"
		
		bill_no = deep_get(data, ['document', 'number'])
		bill_date = getdate( deep_get(data, ['document', 'issue_date']) )
		exists = self.enable_single_invoice(bill_no, bill_date)
		if exists:
			return True, exists

		# Build Purchase Invoice from PO
		doc = make_purchase_invoice(po_ref)
		doc.set_default_number_fields()
		doc.created_with_ai = 1
		doc.bill_no = bill_no
		doc.bill_date = bill_date

		# Prepare extracted items for rate update
		extracted_items = data.get("items") or []

		# Map and update rates: prefer match by index; if "item_code" present then map by code
		changes = []
		if extracted_items and len(extracted_items) == len(doc.items):
			# Build index map for codes if any
			code_to_row = {}
			for idx, row in enumerate(doc.get("items") or []):
				code_to_row.setdefault(row.item_code, []).append((idx, row))

			for i, itm in enumerate(extracted_items):
				# Extract rate if available
				rate = deep_get(itm, ['unit_price', 'value'], 0)
				
				# No rate to update
				if not rate:
					continue

				# !! not found the best method can do
				row_to_update = None
				# Prefer by item_code if present
				itm_code = None
				if itm.get("item_code"):
					itm_code = itm.get("item_code")
				elif (itm.get("attributes") or {}).get("sku"):
					itm_code = (itm.get("attributes") or {}).get("sku")
				if itm_code and itm_code in code_to_row:
					row_to_update = code_to_row[itm_code][0][1]
				elif i < len(doc.items):
					row_to_update = doc.items[i]

				if row_to_update:
					old_rate = flt(row_to_update.rate)
					new_rate = flt(rate)
					if new_rate and new_rate != old_rate:
						row_to_update.rate = new_rate
						changes.append({
							"idx": row_to_update.idx,
							"item_code": row_to_update.item_code,
							"old_rate": old_rate,
							"new_rate": new_rate,
						})

		# Optional GST update if present in payload
		doc.taxes_and_charges = get_gst_template(GST_DEFAULT)
		doc.set_other_charges()

		# Persist
		doc.flags.ignore_mandatory = 1
		doc.flags.ignore_permissions = 1
		doc.flags.ignore_links = 1
		doc.save()

		# add bank account
		self.add_bank_account(data, doc.name)

		# Attach original file if present
		file_doc_name = frappe.db.get_list(
			"File",
			{"attached_to_doctype": "Communication", "attached_to_name": self.inbox},
		)
		for file_name in file_doc_name:
			fn = frappe.get_doc("File", file_name.get("name"))
			self.add_attachment_copy(fn, "Purchase Invoice", doc.name )

		# Mention rate changes only if any
		if changes:
			try:
				frappe.get_doc({
					"doctype": "Comment",
					"reference_doctype": doc.doctype,
					"reference_name": doc.name,
					"comment_type": "Comment",
					"content": json.dumps({"rate_updates": changes}),
				}).insert(ignore_permissions=True)
			except Exception:
				pass

		return True, doc.name
	
	def add_attachment_copy(self, source_file, doctype="", name=""):
		new_file = frappe.new_doc("File")
		doctype = doctype or self.doctype
		name = name or self.name
		new_file.update({
			"doctype": "File",
			"file_name": source_file.file_name,
			"file_url": source_file.file_url,
			"is_private": source_file.is_private,
			"attached_to_doctype": doctype,
			"attached_to_name": name
		})
		new_file.insert()

	def add_bank_account(self, data, name):
		bank_accounts = deep_get(data, ['payment', 'bank_accounts'])
		for d in bank_accounts:
			com = frappe.new_doc("Comment")
			com.comment_type = "Info"
			com.reference_doctype = "Purchase Invoice"
			com.reference_name = name
			com.subject = "Bank Account"
			bank_data = d
			labels = {
				'Bank Name': 'bank_name',
				'Account Name': 'account_name',
				'Account Number': 'account_number',
				'IBAN': 'iban',
				'SWIFT/BIC': 'swift_bic',
				'Bank Address': 'bank_address',
				'Currency': 'currency'
			}
			
			rows = "\n  ".join(
				f"<b>{label}:</b> {bank_data.get(key) or '-'}<br>"
				for label, key in labels.items()
			)

			com.content = f"""
			<div class="frappe-card p-3">
			<h5 class="my-2">Bank Account</h5>
			{rows}
			</div>
			<div class="hidden data">{json.dumps(bank_data)}</div>
			"""
			com.insert(ignore_permissions=True)
		
	def create_purchase_invoice_non_stock(self, data=None):
		"""Create a Non-stock Purchase Invoice purely from the passed parameter.

		Expected payload (simplified): either a dict with keys like
		  - document.number, document.issue_date
		  - supplier.name
		  - currency.code
		  - items: [ { name, description, quantity, unit_of_measure, unit_price.value, amount.value, unit_price.currency } ]
		or the same wrapped under key `result`.

		- Only uses provided parameter; does not read self.data_result or any files.
		- Checks Link masters (Supplier, Currency, UOM, generic Item 'Non-stock'). Missing links are not auto-created;
		  they are recorded to a Comment on the created Purchase Invoice.
		"""

		if not data:
			return False, "Missing data"

		# Normalize input: allow either top-level or wrapped under `result`
		payload = {}
		if isinstance(data, string_types):
			payload = json.loads(data)
		else:
			payload = frappe._dict(data)
		root = payload.get("result") or {}
		if 'result' in root:
			root = root.get("result")
		if not root:
			root = payload

		# Extract primary blocks
		doc_info = (root or {}).get("document") or {}
		supplier_info = (root or {}).get("supplier") or {}
		currency_info = (root or {}).get("currency") or {}
		items_info = (root or {}).get("items") or []
		summary_info = (root or {}).get("summary") or {}
		payment_info = (root or {}).get("payment") or {}

		exists = self.enable_single_invoice(doc_info.get("number"), getdate(doc_info.get("issue_date")))
		if exists:
			return True, exists

		# 2) Gather link existence and collect missing masters for commenting later
		missing_links = {"Supplier": None, "Currency": None, "UOM": [], "Item": []}

		# Supplier
		supplier_name = supplier_info.get("name")
		supplier_exists = None
		if supplier_name:
			supplier_exists = frappe.db.exists("Supplier", supplier_name)
			if not supplier_exists:
				missing_links["Supplier"] = {
					"name": supplier_name,
					"details": supplier_info,
				}

		# Currency
		currency_code = currency_info.get("code") or (summary_info.get("total") or {}).get("currency")
		currency_exists = None
		if currency_code:
			currency_exists = frappe.db.exists("Currency", currency_code)
			if not currency_exists:
				missing_links["Currency"] = {"code": currency_code}

		# UOMs from items
		uom_missing = set()
		for it in items_info:
			uom_nm = (it or {}).get("unit_of_measure") or (it or {}).get("uom")
			if uom_nm:
				if not frappe.db.exists("UOM", uom_nm):
					uom_missing.add(uom_nm)
		if uom_missing:
			missing_links["UOM"] = sorted(uom_missing)
		else:
			missing_links.pop("UOM", None)

		# Ensure generic non-stock Item exists; if not, record it
		if not frappe.db.exists("Item", "Non-stock"):
			missing_links["Item"].append("Non-stock")
		else:
			missing_links.pop("Item", None)

		# 3) Construct Purchase Invoice
		doc = frappe.new_doc("Purchase Invoice")
		doc.created_with_ai = 1
		doc.non_stock_item = 1

		# Header mapping
		# Supplier only if exists
		if supplier_exists:
			doc.supplier = supplier_exists

		# Currency only if exists; otherwise leave blank to record in comment
		if currency_exists:
			doc.currency = currency_code

		# Bill No / Date
		if doc_info.get("number"):
			doc.bill_no = doc_info.get("number")
		if doc_info.get("issue_date"):
			try:
				doc.bill_date = getdate(doc_info.get("issue_date"))
				doc.posting_date = getdate(doc_info.get("issue_date"))
			except Exception:
				pass

		# Remarks: keep simple while still informative
		remarks = []
		refs = (doc_info.get("references") or {})
		po_ref = refs.get("purchase_order_number") if refs else None
		if po_ref:
			remarks.append(f"Reference PO: {po_ref}")
		attn = refs.get("attention") if refs else None
		if attn:
			remarks.append(f"Attention: {attn}")
		terms_desc = (payment_info.get("terms") or {}).get("description") if payment_info else None
		if terms_desc:
			remarks.append(f"Payment Terms: {terms_desc}")
		if remarks:
			doc.remarks = "\n".join(remarks)

		# Items (use generic Non-stock item)
		currency_seen = set()
		for it in items_info:
			qty = it.get("quantity") or it.get("qty")
			rate = None
			if it.get("unit_price") and isinstance(it.get("unit_price"), dict):
				rate = it["unit_price"].get("value")
			elif it.get("rate") is not None:
				rate = it.get("rate")
			amount = None
			if it.get("amount") and isinstance(it.get("amount"), dict):
				amount = it["amount"].get("value")
			elif it.get("amount") is not None:
				amount = it.get("amount")

			uom_nm = it.get("unit_of_measure") or it.get("uom") or None
			it_curr = None
			if it.get("unit_price") and isinstance(it.get("unit_price"), dict):
				it_curr = it["unit_price"].get("currency")
			elif it.get("currency"):
				it_curr = it.get("currency")
			if it_curr:
				currency_seen.add(it_curr)

			if qty:
				row = doc.append("items")
				row.item_code = "Non-stock"
				row.item_name = it.get("name") or it.get("item_name") or "Non-stock"
				row.item_name_view = row.item_name
				row.description = (it.get("description") or "")[:140]
				row.qty = flt(qty)
				if rate is not None:
					row.rate = flt(rate)
				if amount is not None:
					row.amount = flt(amount)
				# Set UOM only if master exists, else leave default and record missing
				if uom_nm and frappe.db.exists("UOM", uom_nm):
					row.uom = uom_nm

		# Currency consistency check similar to v1
		if len(currency_seen) > 1:
			return False, "Multiple currency used on invoice"
		elif currency_seen and not currency_exists:
			# prefer item currency if header currency missing
			ic = list(currency_seen)[0]
			if frappe.db.exists("Currency", ic):
				doc.currency = ic

		doc.taxes_and_charges = get_gst_template(GST_DEFAULT)
		doc.set_other_charges()

		# 4) Persist document; allow saving even if some links are missing
		try:
			doc.save()
		except Exception:
			pass
		if doc.is_new():
			doc.flags.ignore_mandatory = 1
			doc.flags.ignore_permissions = 1
			doc.flags.ignore_links = 1
			doc.flags.ignore_validate = 1
			doc.save()
		
		# add bank account
		self.add_bank_account(data, doc.name)

		# 5) Attach file if `file` docname provided in payload/root
		file_id = (payload.get("file") if isinstance(payload, dict) else None) or (root.get("file") if isinstance(root, dict) else None)
		if file_id:
			try:
				file = frappe.get_doc('File', file_id)
				attachment = frappe.get_doc({
					'doctype': 'File',
					'attached_to_doctype': doc.doctype,
					'attached_to_name': doc.name,
					'file_name': file.file_name,
					'file_url': file.file_url,
					'is_private': file.is_private,
				})
				attachment.insert()
			except Exception:
				pass

		# 6) Post Comment with any missing links and enriched context
		comment_payload = {}
		for k, v in (missing_links or {}).items():
			if v:
				comment_payload.setdefault("missing_links", {})[k] = v
		if comment_payload.get("missing_links"):
			try:
				frappe.get_doc({
					"doctype": "Comment",
					"reference_doctype": doc.doctype,
					"reference_name": doc.name,
					"comment_type": "Comment",
					"content": json.dumps(comment_payload),
				}).insert(ignore_permissions=True)
			except Exception:
				pass

		return True, doc.name

	def enable_single_invoice(self, bill_no, bill_date):
		exists = frappe.db.get_value("Purchase Invoice", {"bill_no":bill_no, "bill_date":bill_date})
		if exists:
			return exists

	def create_invoice2(self, data=""):
		if not data:
			data = json.loads(self.data_result)

		if not data:
			return
	
		# make PI
		doc = make_purchase_invoice(data.get("po_no"))
		doc.set_default_number_fields()
		doc.created_with_ai = 1

		for d in data.get("items"):
			rows = doc.get("items", {"item_code":d['item_code']})
			if rows:
				# rate from PDF
				row = rows[0]
				row.rate = flt(d['rate'])
				row.qty = flt(d['qty'])

		# add GST 
		doc.taxes_and_charges = get_gst_template(GST_DEFAULT)
		doc.set_other_charges()

		doc.flags.ignore_mandatory = 1
		doc.flags.ignore_permissions = 1
		doc.flags.ignore_links = 1
		doc.save()

		file = frappe.get_doc('File', data.get("file"))
		attachment = frappe.get_doc({
			'doctype': 'File',
			'attached_to_doctype': doc.doctype,  # e.g., 'Sales Invoice', 'Purchase Order', etc.
			'attached_to_name': doc.name,    # The name of the document to attach to
			'file_name': file.file_name,
			'file_url': file.file_url,
			'is_private': file.is_private,   # Whether the file is private or public
		})
		attachment.insert()

		return doc.name

# erpnext.ai_agent.doctype.email_invoice.email_invoice.extract_all_bank_data
def extract_all_bank_data():
	# from schduler
	coms = frappe.db.sql("""
		SELECT 
			name, reference_name, reference_doctype, content
		FROM
			`tabComment`
		WHERE
			`subject` = 'Bank Account'
				AND reference_doctype = 'Purchase Invoice'
				AND comment_type = 'Info'
	""", as_dict=1)
	convert_bank_data(coms=coms)

def create_bank_number(doc, method=""):
	if doc.supplier and not doc.bank_number:
		doc.bank_number = convert_bank_data(doc.name)

def convert_bank_data(inv=None, coms=[]):
	from bs4 import BeautifulSoup
	import json

	if not is_doctype_exists("Bank Number"):
		return
	
	def extract_bank_data(text):
		soup = BeautifulSoup(text, "html.parser")
		div = soup.find("div", class_="hidden data")
		json_text = div.get_text(strip=True)
		data = json.loads(json_text)
		return data
	
	def create_bank_data(supplier, bank_data):
		bank_number = cstr(bank_data.get("account_number"))
		bank_number = bank_number.replace("-", "")
		if not bank_number:
			return

		exists = frappe.db.exists("Bank Number", {"bank_number":bank_number})
		if exists:
			return exists

		doc = frappe.new_doc("Bank Number")
		doc.bank_number = bank_number
		doc.bank_account_name = supplier
		doc.bank = get_bank(bank_data.get("bank_name"), bank_data.get("swift_bic"))
		doc.currency = bank_data.get("currency")
		doc.swift = bank_data.get("swift_bic")
		doc.party = supplier
		doc.insert(ignore_permissions=1)
		return doc.name

	# convert Comment WIth data to Supplier Bank Account
	if not coms:
		coms = frappe.db.sql("""
			SELECT 
				name, reference_name, reference_doctype, content
			FROM
				`tabComment`
			WHERE
				`subject` = 'Bank Account'
					AND reference_doctype = 'Purchase Invoice'
					AND comment_type = 'Info'
					AND reference_name = %s
		""", (inv), as_dict=1)

	name = ""
	for d in coms:
		supplier = frappe.db.get_value("Purchase Invoice", d.reference_name, 'supplier')
		# from invoice
		if not supplier:
			continue
		
		bank_data = extract_bank_data(d.content)
		name = create_bank_data(supplier, bank_data)

	return name
	

def get_bank(bank, swift_number):
	# based on swift code
	exists = frappe.db.get_value("Bank", {"swift_number":swift_number})
	if exists:
		return exists
	
	# same name different swift code, this will add new bank record
	base_name = cstr(bank)
	for i in range(20):
		i += 1
		exists = frappe.db.get_value("Bank", {"bank_name":bank})
		if exists:
			bank = f"{base_name} {i}"
		else:
			break
		
	doc = frappe.new_doc("Bank")
	doc.bank_name = bank
	doc.swift_number = swift_number
	doc.insert(ignore_permissions=1)
	return doc.name

	
def extract_domains(items):
    out = []
    seen = set()
    for s in items:
        s = str(s).strip().lower()
        s = re.sub(r'^mailto:', '', s)              # buang mailto:
        s = re.sub(r'^[a-z]+://', '', s)           # buang skema url
        s = s.split('/')[0]                         # buang path
        if '@' in s:
            s = s.rsplit('@', 1)[1]                 # ambil setelah @
        s = re.sub(r'^[\*\.\-]+', '', s)            # buang wildcard/.- di depan
        s = s.split(':')[0]                         # buang port

        # validasi domain sederhana
        if re.match(r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$', s):
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out
	
def get_gst_template(rate):
	rate = flt(rate)
	res = frappe.db.sql("""
		SELECT DISTINCT
			stct.name
		FROM
			`tabPurchase Taxes and Charges Template` stct
				JOIN
			`tabPurchase Taxes and Charges` stc ON stct.name = stc.parent
		WHERE
			stc.rate = {}
				AND stc.parenttype = 'Purchase Taxes and Charges Template';

			   """.format(rate), as_dict=1)
	if res:
		res = res[0]
		return res.get("name")
	else:
		return  ""

def convert_pdf_to_img(path):
	import fitz  # PyMuPDF
	import numpy as np
	from PIL import Image

	try:
		doc = fitz.open(path)

		if doc.needs_pass:
			return False, "Encrypted PDF"

		page = doc[0]
		pix = page.get_pixmap()

		image_np = np.array(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
		return True, image_np

	except Exception as e:
		frappe.log_error(f"convert_pdf_to_img error: {e}")
		return False, str(e)

def find_po_exist(po_no):
	ranges = len(po_no)
	for i in range(ranges):
		if i >= 4:
			break

		res = frappe.db.exists("Purchase Order", {"name":['like', "%"+po_no[i:]]})
		if res:
			return res
		
	return res

import requests, json
def get_erp_data(url_path, filters="", fields="", limit=100):
	# get from ERP prod
	BASE_URL = "https://erp.greenphyto.com"
	API_KEY = frappe.local.conf.prod_api_key
	API_SECRET = frappe.local.conf.prod_api_secret

	api = requests.Session()
	api.headers.update({
		"Authorization": f"token {API_KEY}:{API_SECRET}"
	})

	params = {
		"filters": filters,
		"fields": fields,
		"limit_page_length": limit,
		"order_by": "creation desc"
	}

	res = api.get(f"{BASE_URL}/{url_path}", params=params)

	if res.status_code == 200:
		temp = res.json()
		data = temp.get("data")
		if data:
			return data
		else:
			return {}
	else:
		return {}
	
# pull PO from ERP Production for testing
def pull_erp_po():
	if not frappe.local.conf.enable_pull_po:
		return
	
	filters = [["docstatus", "=", 1]]
	fields = ["name"]

	# filter only on above creation of comment
	# save creation on comment

	po_list = []
	po_list = get_erp_data("api/resource/Purchase Order", json.dumps(filters), json.dumps(fields), 10)

	for p in po_list:
		po_name = p.get("name")
		temp = frappe.db.get_value("Purchase Order", po_name, ["name", "docstatus"], as_dict=1)
		if temp:
			if temp.docstatus == 0:
				doc = frappe.get_doc("Purchase Order", temp.name)
				doc.submit()
			continue

		po = get_erp_data(f"api/resource/Purchase Order/{po_name}")

		if not po:
			continue
		
		po = frappe._dict(po)
		doc = frappe.new_doc("Purchase Order")
		doc.__newname = po_name
		doc.name = po_name

		fields_map = [
			# parent
			"supplier", "transaction_date", "schedule_date", "taxes_and_charges",
			"address_display", "contact_display", "currency", "non_stock_item",

			# child items
			"items.item_code", "items.item_name", "items.item_group", "items.schedule_date", "items.qty", "items.description", 
			"items.item_name_view","items.uom", "items.rate", "items.price_list_rate",

			# child taxes
			"taxes.category", "taxes.add_deduct_tax", "taxes.charge_type", 
			"taxes.account_head", "taxes.description", "taxes.rate"
		]

		tables = {}
		for f in fields_map:
			if "." in f:
				table, field = f.split(".")
				tables.setdefault(table, {})
				if po.get(table):
					for d in po.get(table):
						d = frappe._dict(d)
						tables[table].setdefault(d.name, {})
						tables[table][d.name][field] = d.get(field)

			else:
				doc.set(f, po.get(f))
		
		for nm, val in tables['items'].items():
			row = doc.append("items")
			row.update(val)
			val = frappe._dict(val)
			row.schedule_date = getdate(row.schedule_date)
			row.uom = get_uom(row.uom)
			row.item_code = get_item_copy(val)


		for nm, val in tables['taxes'].items():
			# not yet for account head copy
			row = doc.append("taxes")
			row.update(val)
			val = frappe._dict(val)
		
		doc.supplier = get_supplier_copy(doc.supplier, doc.currency)
		doc.transaction_date = getdate(doc.transaction_date)
		doc.schedule_date = getdate(doc.schedule_date)
		doc.save()
		doc.submit()

	return


def get_supplier_copy(supplier, currency):
	exists = frappe.db.exists("Supplier", supplier)
	if exists:
		return exists
	
	doc = frappe.new_doc("Supplier")
	doc.supplier_group = "All Supplier Groups"
	doc.supplier_type = "Company"
	doc.supplier_name = supplier
	doc.default_currency = currency
	doc.insert()

	return doc.name

def get_item_copy(args):
	exists = frappe.db.exists("Item", args.item_code)
	if exists:
		return exists
	
	item = frappe.new_doc("Item")
	item.item_code = args.item_code
	item.item_name = args.item_name
	item.item_group = get_item_group(args.item_group)
	item.stock_uom = get_uom(args.uom)
	item.description = args.description
	item.insert()

	return item.name

def get_uom(uom):
	exists = frappe.db.exists("UOM", uom)
	if exists:
		return exists
	
	doc = frappe.new_doc("UOM")
	doc.uom_name = uom
	doc.insert()

	return doc.name

def get_item_group(item_group):
	exists = frappe.db.exists("Item Group", item_group)
	if exists:
		return exists
	
	doc = frappe.new_doc("UOM")
	doc.item_group_name = item_group
	doc.insert()

	return doc.name