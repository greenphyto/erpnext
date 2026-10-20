import frappe
from frappe.model.document import Document


class RepeatHarvestGroup(Document):
	def validate(self):
		self.validate_parent_item()
		self.validate_harvest_gap()
		self.validate_harvest_items()

	def validate_parent_item(self):
		if not frappe.db.exists("Item", self.parent_item):
			frappe.throw(f"Parent Item {self.parent_item} does not exist")

	def validate_harvest_gap(self):
		if self.harvest_gap_in_days and self.harvest_gap_in_days < 0:
			frappe.throw("Harvest Gap in Days must be zero or greater")

	def validate_harvest_items(self):
		seen_items = set()
		seen_sequences = set()
		for row in self.get("harvest_items", []):
			if not frappe.db.exists("Item", row.item):
				frappe.throw(f"Row #{row.idx}: Item {row.item} does not exist")

			if row.item == self.parent_item:
				frappe.throw(
					f"Row #{row.idx}: Child item cannot be the same as the parent item"
				)

			if row.item in seen_items:
				frappe.throw(f"Row #{row.idx}: Item {row.item} is duplicated")
			seen_items.add(row.item)

			if row.sequence in seen_sequences:
				frappe.throw(f"Row #{row.idx}: Sequence {row.sequence} is duplicated")
			seen_sequences.add(row.sequence)
