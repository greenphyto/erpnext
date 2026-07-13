import frappe
from frappe.model.document import Document


class RepeatHarvestGroup(Document):
	def validate(self):
		self.validate_parent_item()
		self.validate_harvest_gap()

	def validate_parent_item(self):
		if not frappe.db.exists("Item", self.parent_item):
			frappe.throw(f"Parent Item {self.parent_item} does not exist")

	def validate_harvest_gap(self):
		if self.harvest_gap_in_days and self.harvest_gap_in_days < 0:
			frappe.throw("Harvest Gap in Days must be zero or greater")
