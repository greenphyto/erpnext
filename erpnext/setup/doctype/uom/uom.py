# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class UOM(Document):
	def validate(self):
		if not self.global_description:
			self.global_description = self.uom_name
