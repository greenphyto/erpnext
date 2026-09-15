# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.controllers.uob import UOBAPI

class UOBIntegrationSettings(Document):
	def validate(self):
		self.folder_in = remove_leading_slash(self.folder_in)
		self.folder_out = remove_leading_slash(self.folder_out)

	@frappe.whitelist()
	def get_file_list(self):
		uob = UOBAPI()
		res = uob.get_file_list(limit=200)

		return res

def remove_leading_slash(text: str) -> str:
	return text.lstrip("/")

import requests, base64
from frappe.utils import cint
@frappe.whitelist()
def download_bank_file(fname, decrypt):
	decrypt = cint(decrypt)
	settings = frappe.get_single("UOB Integration Settings")
	url = f"http://{settings.host}/bank/download?dest={settings.folder_out}&fname={fname}&decrypt={decrypt}&raw=0"
	r = requests.get(url)

	if r.status_code != 200:
		frappe.throw("Failed to get file.")

	if decrypt:
		fname = fname.replace(".pgp", "")

	res = r.json()

	if res and res.get("file"):
		file_bytes = base64.b64decode(res.get("file"))

		frappe.local.response.filename = res.get("filename")
		frappe.local.response.filecontent = file_bytes
		frappe.local.response.type = "download"