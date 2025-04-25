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
		res = uob.get_file_list()

		return res

def remove_leading_slash(text: str) -> str:
	return text.lstrip("/")
