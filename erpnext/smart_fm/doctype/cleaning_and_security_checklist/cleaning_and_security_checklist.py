# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe import _

class CleaningandSecurityChecklist(Document):
	def validate(self):
		self.validate_template()

	def validate_template(self):
		if frappe.db.get_value("Checklist Template", self.template, "enable") == 0:
			frappe.throw(_("Cannot use Template <b>{}</b>!".format(self.template)))

	def validate_checklist_input(self):
		for d in self.get("checklist"):
			if cint(d.is_group):
				d.value = 0

	@frappe.whitelist()
	def load_template_indicator(self):
		checklist = load_template_indicator_web(self.template)
		self.checklist = []
		for d in checklist:
			row = self.append("checklist")
			row.update(d)

		return checklist

@frappe.whitelist()
def load_template_indicator_web(template, is_new=0):
	doc = frappe.get_doc("Checklist Template", template)
	checklist = []
	if not template:
		return checklist
	
	for d in doc.get("indicators"):
		row = {}
		fields = ["indicator", "is_group", "indent", "description"]
		for f in fields:
			row[f] = d.get(f)
		
		if is_new:
			row['name'] = frappe.generate_hash("", 8)
			row['__islocal'] = 1
			row['__unsaved'] = 1

		checklist.append(row)
	
	return checklist
