# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import csv
import io
from frappe.utils import now_datetime
from frappe.model.document import Document
from erpnext.controllers.uob import UOBAPI
import traceback

class UOBSyncLog(Document):
	def send_file(self, force=False):
		if not force and self.status == "Complete":
			return
		uob = UOBAPI()
		fn = frappe.get_doc("File", self.file)
		filepath = fn.get_full_path()
		filename = fn.file_name
		res = uob.upload_bank_tx(filepath, filename)
		if "filename" in res:
			self.db_set("status", "Complete")
		else:
			self.db_set("status", "Error")
			error = res.get("error") or "Unknown"
			self.db_set("error", error)

def create_log(csv_data, filename=""):
	# create log
	doc = frappe.new_doc("UOB Sync Log")
	doc.insert(ignore_permissions=1)

	try:
		# make CSV
		fn = save_csv_to_file(csv_data, filename, doc.doctype, doc.name)
		doc.file = fn.name
		doc.filepath = fn.file_url
		doc.save()
		# send
		doc.send_file()
	except Exception as e:
		tb_str = traceback.format_exc()
		doc.db_set("status", "Error")
		doc.db_set("error", tb_str)
	

def save_csv_to_file(data: list[list[str]], filename: str = None, attach_to_doctype="", attach_to_name="") -> str:
	if not data or not isinstance(data, list):
		frappe.throw("Data must be a non-empty list of rows")

	if not filename:
		timestamp = now_datetime().strftime("%Y%m%d_%H%M%S")
		filename = f"data_export_{timestamp}.csv"

	csv_buffer = io.StringIO()
	writer = csv.writer(csv_buffer)
	for row in data:
		writer.writerow(row)

	content = csv_buffer.getvalue()
	csv_buffer.close()

	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": filename,
		"is_private": 1,
		"content": content,
		"attached_to_doctype": attach_to_doctype,
		"attached_to_name": attach_to_name,
	})
	file_doc.insert(ignore_permissions=True)

	return file_doc  # atau file_doc.name kalau perlu nama dokumen
