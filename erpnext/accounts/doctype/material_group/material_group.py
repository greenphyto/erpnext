# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint
from frappe import _
from frappe.model.document import Document

class MaterialGroup(Document):
	def validate(self):
		self.valdiate_number_range()

	def valdiate_number_range(self)
		if cint(self.number_end) < cint(self.number_start):
			frappe.throw(_("Number end must be grater than start"))
