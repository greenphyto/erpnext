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
