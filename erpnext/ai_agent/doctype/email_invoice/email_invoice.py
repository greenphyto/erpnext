# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
from erpnext.controllers.va2 import extract_invoice_data, get_po_number, get_item_detail, get_po_and_items
from frappe.utils import flt, getdate, get_time
from erpnext.controllers.erp import get_supplier_context
import os
from frappe.utils import get_traceback

MAX_DISPLAY_LENGTH = 1000
SHORT_HEAD = 300
SHORT_TAIL = 700
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
			self.unknown_reason = text[:1000]
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
			self.unknown_reason = ""
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

	def process_email(self, doc={}):
		result = []
		self._init_reasons()
		if not doc and self.inbox:
			doc = frappe.get_doc("Communication", self.inbox)

		msg = doc.get("content")

		# should check if this invoice or not
		file_doc_name = frappe.db.get_list("File", {
			"attached_to_doctype":"Communication",
			"attached_to_name":doc.name
		})
		
		# temporary detect invoice or not by attachment
		if not file_doc_name:
			self.add_reason(
				category="attachment",
				code="no_attachment",
				message="No attachments found on the email"
			)
			self._finalize_reasons()
			return
		
		supp_context = get_supplier_context()
		for file_name in file_doc_name:
			
			fn = frappe.get_doc('File', file_name.get("name"))

			# check valid file
			full_path = fn.get_full_path()
			if not os.path.exists(full_path):
				self.add_reason(
					category="attachment",
					code="missing_file",
					message="Attached file not found on server",
					context={"file": fn.file_name, "url": fn.file_url}
				)
				continue

			# copy attachment to current email
			self.add_attachment_copy(fn)

			if ".pdf" in full_path.lower():
				res, img_or_msg = convert_pdf_to_img(full_path)
				if not res:
					msg = img_or_msg or "PDF conversion failed"
					code = "encrypted_pdf" if "encrypted" in msg.lower() else "pdf_conversion_failed"
					self.add_reason(
						category="pdf",
						code=code,
						message=msg[:200],
						context={"file": fn.file_name}
					)
					continue
			else:
				# not pdf
				self.add_reason(
					category="attachment",
					code="not_pdf",
					message="Attachment is not a PDF",
					context={"file": fn.file_name}
				)
				continue 

			if frappe.flags.in_test:
				temp = json.loads(self.get("data_result") or "[]")
				if temp:
					temp = {"result":temp[0]}
			else:
				temp = get_po_and_items(full_path, supp_context, self.sender)

			if temp and temp.get("result"):
				result = temp["result"]
				temp_po = result.get("po_no") or result.get("purchase_order")
				po_no = find_po_exist(temp_po)
				if po_no:
					# convert from existing PO
					if not self.po_no:
						self.po_no = po_no
						
					po = frappe.get_doc("Purchase Order", po_no)
					items = []
					for d in po.items:
						items.append(
							{"item_code": d.item_name, "qty":d.qty, "rate":d.rate, "uom":d.uom}
						)

					result.append({
						"po_no":po_no,
						"items":items,
						"file":fn.name
					})
				elif temp["result"].get("supplier"):
					# make new non-stock Item
					items = temp["result"]["items"]
					supplier = temp["result"]["supplier"]
					result.append({
						"po_no":"",
						"items":items,
						"file":fn.name,
						"supplier":supplier.get("supplier_name")
					})
			else:
				self.add_reason(
					category="agent",
					code="no_extraction_result",
					message="AI agent returned no result",
					context={"file": fn.file_name}
				)

		# If nothing usable, record reasons and exit early
		if not result:
			self._finalize_reasons()
			return

		self.data_result = json.dumps(result)
		self.create_invoice_result(result, doc)

	def create_invoice_result(self, result=[], com_doc=""):
		if not com_doc and self.inbox:
			com_doc = frappe.get_doc("Communication", self.inbox)

		if not result and self.data_result:
			result = json.loads(self.data_result)

		pi = []
		for res in result:
			name = None
			try:
				if res.get("po_no"):
					name = self.create_invoice(res)
				else:
					r, name = self.create_purchase_invoice_non_stock(res)
					if not r:
						self.add_reason(
							category="pi",
							code="create_failed",
							message=str(name)
						)
						frappe.throw(name)

			except Exception as e:
				name = ""
				self.add_reason(
					category="system",
					code="exception",
					message=f"{e}"
				)
				self.error_trace = get_traceback()

			if name:
				com_doc.db_set("reference_doctype", "Purchase Invoice")
				com_doc.db_set("reference_name", name)
				if not self.invoice_no:
					self.invoice_no = name

				pi.append(name)

		# If we produced no PI, make sure reasons are visible and short reason set
		if not pi:
			self._finalize_reasons()
		self.set_status()
		return pi
	
	def add_attachment_copy(self, source_file):
		new_file = frappe.new_doc("File")
		new_file.update({
			"doctype": "File",
			"file_name": source_file.file_name,
			"file_url": source_file.file_url,
			"is_private": source_file.is_private,
			"attached_to_doctype": self.doctype,
			"attached_to_name": self.name
		})
		new_file.insert()

	def create_invoice(self, data=""):
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
		doc.taxes_and_charges = get_gst_template(data.get("gst_percent") or 9)
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
	
	def create_purchase_invoice_non_stock(self, data=None):
		if not data:
			data = json.loads(self.data_result)

		if not data:
			return False, "Missing data"
		
		items=data.get("items")
		supplier=data.get("supplier")
		file_name=data.get("file")

		if not items:
			return False, "Cannot recognise item"
		
		doc = frappe.new_doc("Purchase Invoice")
		doc.supplier = frappe.db.exists("Supplier", supplier)
		doc.non_stock_item = 1
		doc.created_with_ai = 1
		currency = []
		for d in items:
			if d.get("qty"):
				row = doc.append("items")
				row.item_code = "Non-stock"
				row.item_name = d.get("item_name")
				row.item_name_view = d.get("item_name")
				row.qty = flt(d.get("qty"))
				row.rate = flt(d.get("rate"))
				row.uom = get_uom(d.get("uom") or "Nos")
				row.amount = flt(d.get("amount"))
				curr = d.get("currency")
				if curr and curr not in currency:
					currency.append(curr)
		
		if not doc.get("items"):
			return False, "Item is empty"
		
		if len(currency) > 1:
			return False, "Multiple currencies detected in this invoice"
		if currency:
			doc.currency = currency[0]
		else:
			doc.currency = "SGD"			

		# add GST
		doc.taxes_and_charges = get_gst_template(data.get("gst_percent") or 9)
		doc.set_other_charges()
		
		doc.flags.ignore_mandatory = 1
		doc.flags.ignore_permissions = 1
		doc.flags.ignore_links = 1
		doc.save()

		file = frappe.get_doc('File', file_name)
		attachment = frappe.get_doc({
			'doctype': 'File',
			'attached_to_doctype': doc.doctype,  # e.g., 'Sales Invoice', 'Purchase Order', etc.
			'attached_to_name': doc.name,    # The name of the document to attach to
			'file_name': file.file_name,
			'file_url': file.file_url,
			'is_private': file.is_private,   # Whether the file is private or public
		})
		attachment.insert()

		return True, doc.name
	
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

def find_po_exist(po_list):
	if po_list:
		po_no = po_list[0]
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


