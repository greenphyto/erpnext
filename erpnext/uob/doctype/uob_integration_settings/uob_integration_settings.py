# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.controllers.uob import UOBAPI

class UOBIntegrationSettings(Document):
	@frappe.whitelist()
	def get_file_list(self):
		uob = UOBAPI()
		res = uob.get_flle_list()

		return res
