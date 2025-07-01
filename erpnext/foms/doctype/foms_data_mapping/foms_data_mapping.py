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


def create_foms_data(data_type, data_name, raw, reopen=False):
	name = frappe.db.exists("FOMS Data Mapping", {
		"data_type":data_type,
		"data_name":data_name,
	})

	if name:
		doc = frappe.get_doc("FOMS Data Mapping", name)
		if reopen:
			doc.doc_type = ""
			doc.doc_name = ""

		elif doc.doc_type and not frappe.db.exists(doc.doc_type, doc.doc_name):
			doc.doc_name = ""
	else:
		doc = frappe.new_doc("FOMS Data Mapping")
		doc.data_type = data_type
		doc.created_on = now()
	
	if doc.status == "Mapped":
		doc.status = "Unknown"
		doc.doc_type = ""
		doc.doc_name = ""

	doc.data_name = data_name
	doc.raw_data = json.dumps(raw, default=str)
	doc.last_sync = now()

	try:
		doc.save()
	except:
		pass

	return doc

def make_in_progress(log_name, inprogress=True, commit=False):
	frappe.db.set_value("FOMS Data Mapping", log_name, "status", "In Progress" if inprogress else "Unknown")
	if commit:
		frappe.db.commit()
	return True

def update_data_result(data_type, data_name, result_name, result_doctype="", name_id=None):
	if not name_id:
		name_id = frappe.db.exists("FOMS Data Mapping", {
			"data_type":data_type,
			"data_name":data_name,
		})
		
	if name_id:
		log = frappe.get_doc("FOMS Data Mapping", name_id)
		log.doc_name = result_name
		log.doc_type = result_doctype or log.data_type
		log.save()