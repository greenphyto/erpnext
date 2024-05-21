# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class WorkstationType(Document):
	def before_save(self):
		self.validate_calculation_type()
		self.set_hour_rate()

	def set_hour_rate(self):
		self.hour_rate = (
			flt(self.hour_rate_labour)
			+ flt(self.hour_rate_electricity)
			+ flt(self.hour_rate_consumable)
			+ flt(self.hour_rate_rent)
		)

		self.per_qty_rate = (
			flt(self.per_qty_rate_electricity)
			+ flt(self.per_qty_rate_wages)
			+ flt(self.per_qty_rate_machinery)
		)

	def validate_calculation_type(self):
		if self.calculation_type == "Per Qty":
			self.hour_rate = 0
			self.hour_rate_labour = 0
			self.hour_rate_electricity = 0
			self.hour_rate_consumable = 0
			self.hour_rate_rent = 0
		else:
			self.per_qty_rate = 0
			self.per_qty_rate_electricity = 0
			self.per_qty_rate_wages = 0
			self.per_qty_rate_machinery = 0

def get_workstations(workstation_type):
	workstations = frappe.get_all("Workstation", filters={"workstation_type": workstation_type})

	return [workstation.name for workstation in workstations]
