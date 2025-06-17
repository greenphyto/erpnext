# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
from erpnext.controllers.va2 import extract_invoice_data, get_po_number, get_item_detail
from frappe.utils import flt, getdate, get_time
class EmailInvoice(Document):
	def validate(self):
		self.set_status()

	def set_status(self):
		if self.po_no:
			if self.invoice_no:
				self.status = "Matched"
			else:
				self.status = "Pending"
		else:
			self.status = "Unknown"

	def sync_email(self, comm_name="", doc=None):
		if not doc:
			doc = frappe.get_doc("Communication", comm_name)
		self.sender = doc.sender
		self.cc = doc.cc
		self.bcc = doc.bcc
		self.message = doc.content
		self.received_date = getdate(doc.communication_date)
		self.time = get_time(doc.communication_date)
		self.subject = doc.subject
		self.message_id = doc.message_id
		self.inbox = doc.name
		self.process_email(doc)

	def process_email(self, doc=None):
		result = []
		msg = doc.content

		# should check if this invoice or not
		file_doc_name = frappe.db.get_list("File", {
			"attached_to_doctype":"Communication",
			"attached_to_name":doc.name
		})
		
		# temporary detect invoice/not by attachment
		if not file_doc_name:
			return
		
		for file_name in file_doc_name:
			
			fn = frappe.get_doc('File', file_name)
			fn_name = fn.file_name
			full_path = fn.get_full_path()
			if ".pdf" in full_path:
				full_path = convert_pdf_to_img(full_path)

			temp = get_po_number(full_path)
			if temp and temp.get("result"):
				# here
				po_no = find_po_exist(temp.get("result"))
				if not po_no:
					continue
				
				if not self.po_no:
					self.po_no = po_no
					
				po = frappe.get_doc("Purchase Order", po_no)
				items = []
				for d in po.items:
					items.append(
						{"item_code": d.item_name, "qty":d.qty, "rate":d.rate, "uom":d.uom}
					)

				# temporary not used
				items = get_item_detail(full_path, items)
				result.append({
					"po_no":po_no,
					"items":items,
					"file":file_name
				})

		pi = []
		for res in result:
			name = self.create_invoice(res)
			doc.db_set("reference_doctype", "Purchase Invoice")
			doc.db_set("reference_name", name)
			if not self.invoice_no:
				self.invoice_no = name

			pi.append(name)


		self.set_status()
		return pi

	def create_invoice(self, data):
		# make PI
		doc = make_purchase_invoice(data.get("po_no"))
		doc.created_with_ai = 1

		for d in data.get("items"):
			rows = doc.get("items", {"item_code":d['item_code']})
			if rows:
				row = rows[0]
				row.rate = flt(d['rate'])
				row.qty = flt(d['qty'])
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

def convert_pdf_to_img(path):
	import fitz  # PyMuPDF
	import numpy as np
	from PIL import Image

	doc = fitz.open(path)

	page = doc[0]

	pix = page.get_pixmap()

	image_np = np.array(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))

	return image_np

def find_po_exist(po_no):
	ranges = len(po_no)
	for i in range(ranges):
		res = frappe.db.exists("Purchase Order", {"name":['like', "%"+po_no[i:]]})
		if res:
			return res
		
	return res