# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RateCard(Document):
	def validate(self):
		self.create_workstation()

	def create_workstation(self):
		for d in self.rates:
			if not frappe.db.exists("Workstation", d.workstation):
				workstation_name = f"{self.title}-{d.operation}"
				ws = frappe.new_doc("Workstation")
				ws.update({
					"workstation_name": workstation_name,
					"operation": d.operation,
					"calculation_type": "Per KG",
					"per_qty_rate_electricity": d.electricity,	
					"per_qty_rate_wages": d.manpower,
					"per_qty_rate_machinery": d.machinery,
					"per_qty_rate_consumable": d.consumable,
				})
				ws.insert()
				d.workstation = ws.name
			else:
				# update existsing workstation rates
				ws = frappe.get_doc("Workstation", d.workstation)
				ws.per_qty_rate_electricity = d.electricity
				ws.per_qty_rate_wages = d.manpower
				ws.per_qty_rate_machinery = d.machinery
				ws.per_qty_rate_consumable = d.consumable
				ws.save()	
			
