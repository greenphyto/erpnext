# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class QRCodeData(Document):
	def autoname(self):
		self.name = "QR"+frappe.generate_hash(length=8)


