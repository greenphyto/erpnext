# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CropAnomalyReport(Document):
	def validate(self):
		self.validate_affected_quantities()

	def validate_affected_quantities(self):
		if self.num_cages_affected and self.total_cages_in_lot:
			if self.num_cages_affected > self.total_cages_in_lot:
				frappe.throw(
					frappe._("Number of Cages Affected ({0}) cannot exceed Total Cages in Lot ({1})").format(
						self.num_cages_affected, self.total_cages_in_lot
					)
				)

		if self.num_trays_affected and self.total_trays_in_lot:
			if self.num_trays_affected > self.total_trays_in_lot:
				frappe.throw(
					frappe._("Number of Trays Affected ({0}) cannot exceed Total Trays in Lot ({1})").format(
						self.num_trays_affected, self.total_trays_in_lot
					)
				)
