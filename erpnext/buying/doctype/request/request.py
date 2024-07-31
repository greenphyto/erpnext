# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.utils import getdate, flt
from frappe import _
from erpnext.controllers.foms import UOM_MAP
from six import string_types
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

	def sync_request_so(self):
		so_name = frappe.db.exists("Sales Order", {"request_no":self.name, "docstatus":1})
		if not so_name:
			return
		
		doc = frappe.get_doc("Sales Order", so_name)
		doc.delivery_date = getdate(self.delivery_date)
		update_list = []
		for d in self.get("items"):
			items = doc.get("items", {"item_code":d.item_code})
			if items:
				item = items[0]
				item.delivery_date = getdate(self.delivery_date)
				item.qty = d.qty
				update_list.append(d)

		doc.validate()
		for item in doc.get("items"):
			item.db_update()
		doc.db_update()


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

@frappe.whitelist()
def create_sales_order(request_name):
	req = frappe.get_doc("Request", request_name)

	exists = frappe.get_value("Sales Order", {"request_no":req.name})
	if exists:
		return exists
	
	# new doc
	doc = frappe.new_doc("Sales Order")
	doc.customer = "Internal Customer"
	doc.delivery_date = getdate(req.delivery_date)
	doc.request_no = req.name

	# set value
	for d in req.get("items"):
		row = doc.append("items")
		row.item_code = d.item_code
		if d.uom == "Package":
			row.weight_order = 0
		else:
			row.weight_order = 1
		row.package = d.packaging
		row.qty_order = d.qty

		# need convertion from package vs stock qty
		row.qty = d.qty
		row.uom = d.uom

	# internal customer
	doc.insert(ignore_permissions=1)
	doc.submit()

	return doc.name

@frappe.whitelist()
def update_request(request_no, items, delivery_date=""):
	"""
	# only can change qty, not for package
	# can delete or add?
	items = [
		{
			"item_code":"",
			"qty":0,
			"uom":"",
			"packaging":"",
			"delete":False
		}
	]
	"""

	if isinstance(items, string_types):
		items = json.loads(items)

	doc = frappe.get_doc("Request", request_no)
	if delivery_date:
		doc.delivery_date = getdate(delivery_date)
	
	for d in items:
		d = frappe._dict(d)
		items = doc.get("items", {"item_code":d.item_code})
		if items:
			item = items[0]
			item.qty = d.qty
			item.db_update()

	doc.validate()
	doc.sync_request_so()
	doc.db_update()

	return request_no