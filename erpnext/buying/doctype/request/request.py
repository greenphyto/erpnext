# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt
from frappe import _
from erpnext.controllers.foms import UOM_MAP
class Request(Document):
	def validate(self):
		self.calculate_price()
		self.calculate_weight()
		self.validate_date()

	def validate_date(self):
		if getdate(self.delivery_date) < getdate(self.posting_date):
			frappe.throw(_("Delivery Date cannot before posting date."))

	def calculate_price(self):
		self.total_price = 0
		for d in self.get("items"):
			d.amount = flt(d.rate) * flt(d.qty)
			self.total_price += d.amount

	def calculate_weight(self):
		self.total_weight = 0
		for d in self.get("items"):
			d.weight = flt(d.unit_weight) * flt(d.qty)
			self.total_weight += d.weight


def create_request_form(data):

	# find exists

	name = frappe.db.exists("Request", {"foms_order_id":data.foms_order_id})
	if name:
		doc = frappe.get_doc("Request", name)
		return doc.name
	else:
		doc = frappe.new_doc("Request")
	
	# set department if exist
	dept = frappe.db.exists("Departemnt", data.department)
	doc.department = dept

	# create packaging if missing
	for d in data.get("items"):
		d = frappe._dict(d)
		row = doc.append("items")
		row.update(d)
		row.packaging = get_packaging_name(d.packaging, d.unit_qty, d.unit_uom, d.unit_weight)
	
	doc.insert(ignore_permissions=1)

	return doc.name

def get_packaging_name(packaging, qty, uom, total_weight):
	pack = frappe.db.exists("Packaging", packaging)
	if pack:
		return pack
	else:
		doc = frappe.new_doc("Packaging")
		doc.title = packaging
		doc.description = packaging
		doc.quantity = flt(qty)
		doc.uom = UOM_MAP.get(uom) or uom
		doc.total_weight = flt(total_weight)
		doc.insert(ignore_permissions=1)
		return doc.name

