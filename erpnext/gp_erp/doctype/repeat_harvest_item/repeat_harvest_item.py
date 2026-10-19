import frappe
from frappe.model.document import Document


class RepeatHarvestItem(Document):
	def validate(self):
		self.validate_item()
		self.validate_group_active()
		self.validate_no_duplicates()
		self.validate_status_transition()

	def validate_item(self):
		if not frappe.db.exists("Item", self.item):
			frappe.throw(f"Item {self.item} does not exist")

	def validate_group_active(self):
		if self.repeat_harvest_group:
			is_active = frappe.db.get_value(
				"Repeat Harvest Group", self.repeat_harvest_group, "is_active"
			)
			if not is_active:
				frappe.throw("Cannot create item for inactive Repeat Harvest Group")

	def validate_no_duplicates(self):
		existing = frappe.db.exists(
			"Repeat Harvest Item",
			{
				"repeat_harvest_group": self.repeat_harvest_group,
				"item": self.item,
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(f"Item {self.item} already exists in this group")

		existing_seq = frappe.db.exists(
			"Repeat Harvest Item",
			{
				"repeat_harvest_group": self.repeat_harvest_group,
				"sequence": self.sequence,
				"name": ["!=", self.name],
			},
		)
		if existing_seq:
			frappe.throw(f"Sequence {self.sequence} already exists in this group")

	def validate_status_transition(self):
		if self.is_new():
			return

		old_status = frappe.db.get_value("Repeat Harvest Item", self.name, "status")
		if self.status == old_status:
			return

		valid_transitions = {
			"Draft": ["Planned", "Cancelled"],
			"Planned": ["In Progress", "Cancelled"],
			"In Progress": ["Completed", "Cancelled"],
			"Completed": [],
			"Cancelled": [],
		}

		allowed = valid_transitions.get(old_status, [])
		if self.status not in allowed:
			frappe.throw(
				f"Cannot transition from {old_status} to {self.status}. "
				f"Allowed: {', '.join(allowed) if allowed else 'none'}"
			)
