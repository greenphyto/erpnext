# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe import _

class QRCodeData(Document):
	def autoname(self):
		length = 3
		for d in range(10):
			name = "QR"+frappe.generate_hash(length=length)
			if not frappe.db.exists("QR Code Data", name):
				self.name = name
				return self.name
			else:
				length += 1

	def validate(self):
		self.validate_reference()
		self.validate_json()
	
	def validate_reference(self):
		if not self.doc_type or not self.doc_name:
			return
		
		if not frappe.db.exists(self.doc_type, self.doc_name):
			frappe.throw(_("Document <b>{} {}</b> is not exists!".format(self.doc_type, self.doc_name)))

	def validate_json(self):
		if not self.data:
			return
		
		data_temp = json.dumps(self.data, sort_keys=True)
		self.data = data_temp

	def get_data(self):
		if self.doc_type and self.doc_name:
			doc = frappe.get_doc(self.doc_type, self.doc_name)
			return doc.as_dict()
		else:
			return json.loads(self.data)


