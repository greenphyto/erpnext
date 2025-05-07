# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
import csv
import io
from frappe.utils import now_datetime, cint
from frappe.model.document import Document
from erpnext.controllers.uob import UOBAPI
import traceback
import base64
from frappe.utils.file_manager import save_file

class UOBSyncLog(Document):
	def __init__(self, *args, **kwargs):
		super(UOBSyncLog, self).__init__(*args, **kwargs)
		self.uob = UOBAPI()

	def send_file(self, force=False):
		if not force and self.status == "Complete":
			return
		fn = frappe.get_doc("File", self.file)
		filepath = fn.get_full_path()
		filename = fn.file_name
		res = self.uob.upload_bank_tx(filepath, filename)
		self.save_result(res)

	def save_result(self, res):
		self.db_set("status_code", cint(res.get("status_code")))
		if res.get("status_code") == 200:
			self.db_set("status", "Complete")
		else:
			self.db_set("status", "Error")
			error = res.get("result") or res.get("error")
			self.db_set("error", json.dumps(error))
	
	def download_file(self, filename):
		temp = self.uob.download_bank_tx(fname=filename)
		self.save_result(temp)

		self.db_set("status_code", cint(temp.get("status_code")))
		if "result" in temp:
			res = temp['result']
			encoded_data = res.get("file")
			binary_data = base64.b64decode(encoded_data)
			folder="Home/Attachments"

			saved_file = save_file(
					filename,        # fname (nama file)
					binary_data,     # file content dalam bytes
					self.doctype,            # dt = tidak ada dokumen
					self.name,            # dn = tidak ada nama dokumen
					folder=folder,
					is_private=1
				)

			return saved_file.file_url


def create_upload_log(csv_data, filename=""):
	# create log
	doc = frappe.new_doc("UOB Sync Log")
	doc.type = "Upload"
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
		doc.db_set("status_code", 0)

def create_download_log(filename):
	doc = frappe.new_doc("UOB Sync Log")
	doc.type = "Download"
	doc.insert(ignore_permissions=1)

	doc.download_file(filename)

	

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

def get_new_payment_file():
	uob = UOBAPI()
	res = uob.get_file_list()
	for d in res.get("result"):
		# save
		create_download_log(d.get("name"))
	# download
	# save
	# read
	# process