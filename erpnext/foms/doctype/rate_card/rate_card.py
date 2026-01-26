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
			

def update_bom_item(doc, method=""):
	# update BOM to ralated rate card
	if doc.rate_card:
		rate_card = frappe.get_doc("Rate Card", doc.rate_card)
		# get BVOM default
		bom = frappe.get_doc("BOM", doc.default_bom)

		# set new-version
		new_bom = frappe.copy_doc(bom)
		new_bom.is_default = 1
		allow_create_new = False
		for d in rate_card.rates:
			for op in new_bom.operations:
				if op.operation == d.operation:
					if op.workstation != d.workstation:
						allow_create_new = True
					op.workstation = d.workstation
					op.calculation_type = "Per KG"
					op.wages_cost = d.manpower
					op.electricity_cost = d.electricity
					op.machinery_cost = d.machinery
					op.consumable_cost = d.consumable
					
		if allow_create_new:
			new_bom.insert()
			new_bom.submit()
			doc.default_bom = new_bom.name