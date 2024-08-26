# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.utils import now

class FOMSDataMapping(Document):
	def validate(self):
		self.set_status()

	def get_data(self):
		return json.loads(self.raw_data)

	def set_status(self):
		if self.doc_type and self.doc_name:
			self.status = "Mapped"
		else:
			self.status = "Unknown"


def create_foms_data(data_type, data_name, raw):
	name = frappe.db.exists("FOMS Data Mapping", {
		"data_type":data_type,
		"data_name":data_name,
	})

	if name:
		doc = frappe.get_doc("FOMS Data Mapping", name)
		if not frappe.db.exists(doc.doc_type, doc.doc_name):
			doc.doc_name = ""
	else:
		doc = frappe.new_doc("FOMS Data Mapping")
		doc.data_type = data_type
		doc.data_name = data_name
		doc.created_on = now()
	
	doc.raw_data = json.dumps(raw)
	doc.last_sync = now()

	doc.save()

	return doc

def update_data_result(data_type, data_name, result_name, doc_type=""):
	name = frappe.db.exists("FOMS Data Mapping", {
		"data_type":data_type,
		"data_name":data_name,
	})
	if name:
		log = frappe.get_doc("FOMS Data Mapping", name)
		log.doc_name = result_name
		log.doc_type = doc_type or log.data_type
		log.save()