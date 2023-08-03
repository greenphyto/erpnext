# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr

class ChecklistTemplate(Document):
	def validate(self):
		self.fix_indent_and_group()

	def fix_indent_and_group(self):
		group_list = []
		cur_indent = 0
		for d in self.get("indicators"):
			if cint(d.is_group):
				# cut
				group_list = group_list[: cint(d.indent)]
				group_list.append(d)
				if len(group_list) >= cint(d.indent) + 1:
					continue
				else:
					right_indent = len(group_list) - 1
					d.indent = cstr(right_indent)
			else:
				if cint(d.indent) < len(group_list):
					group_list = group_list[: cint(d.indent)]

				if len(group_list) > cint(d.indent) - 1:
					continue
				else:
					right_indent = len(group_list)
					d.indent = cstr(right_indent)

			


@frappe.whitelist()
def get_template_enable(**args):
	return frappe.db.get_all("Checklist Template", {"enable": 1}, ['name as label', "name as value"])
