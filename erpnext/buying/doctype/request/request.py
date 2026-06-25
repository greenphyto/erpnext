# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json, erpnext
from frappe.model.document import Document
from frappe.utils import getdate, flt, cstr
from frappe import _
from erpnext.controllers.foms import UOM_MAP
from six import string_types
class Request(Document):
	def validate(self):
		self.calculate_price()
		self.calculate_weight()
		self.validate_date()
		self.export_salad_items()
		self.set_status()

	def on_cancel(self):
		self.set_status()

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

	def set_status(self, db_update=False):
		if self.docstatus == 0:
			self.status = "Draft"
		elif self.docstatus == 2:
			self.status = "Cancelled"
		elif self.delivery_percent >= 100:
			self.status = "Completed"
		else:
			self.status = "Submitted"
		
		if db_update:
			self.db_set("status", self.status)

	def set_delivery_percent(self, db_update=False):
		percent = []
		for d in self.items:
			percent.append(flt(d.delivery_percent))

		pc = sum(percent)/len(percent)
		self.delivery_percent = pc
		if db_update:
			self.db_set("delivery_percent", self.delivery_percent)

		self.set_status(db_update)
	def export_salad_items(self):
		self.salad_items = []
		for d in self.items:
			if d.get("is_salad_product"):
				bom = frappe.get_doc("BOM", d.salad_recipe)
				for item in bom.get("items"):
					row = self.append("salad_items")
					row.item_code = item.item_code
					row.qty = item.qty * d.qty
					row.stock_qty = item.stock_qty * d.qty
					row.conversion_factor = item.conversion_factor
					row.uom = item.uom
					row.rate = item.rate
					row.amount = item.amount * item.qty
					row.bom = bom.name
					row.parent_item = d.item_code
					row.bom_no = frappe.get_value("Item", row.item_code, "default_bom")
					if not row.bom_no:
						row.progress = 100
				
				progress = []
				for d in self.salad_items:
					if d.progress:
						progress.append(d.progress)
				
				d.progress = sum(progress)/len(progress)



def create_request_form(data):

	# find exists

	name = frappe.db.exists("Request", {"foms_id":data.foms_order_id})
	if name:
		doc = frappe.get_doc("Request", name)
		return doc.name
	else:
		doc = frappe.new_doc("Request")
	
	if not data.company:
		data.company = erpnext.get_default_company()
		
	# set department if exist
	dept = frappe.db.exists("Departemnt", data.department)
	doc.department = dept
	doc.company = data.company

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

	exists = frappe.get_value("Sales Order", {"request_no":req.name, "docstatus":['!=', 2]})
	if exists:
		return exists
	
	# new doc
	doc = frappe.new_doc("Sales Order")
	doc.customer = "Internal Customer"
	doc.delivery_date = getdate(req.delivery_date)
	doc.request_no = req.name
	doc.po_no = req.name

	non_package_item = 0

	# set value
	for d in req.get("items"):
		row = doc.append("items")
		row.item_code = d.item_code
		if d.uom == "Package":
			non_package_item = 0
		else:
			non_package_item = 1
		row.uom = d.packaging
		row.weight_in_unit = d.unit_weight
		row.qty = d.qty

	doc.non_package_item = non_package_item

	# internal customer
	doc.save()
	# doc.insert(ignore_permissions=1)
	doc.submit()

	return doc.name

@frappe.whitelist()
def get_events(start, end, user=None, filters=None, item_codes=None):
	"""Fetch Request events for calendar view."""
	from frappe.desk.reportview import get_filters_cond

	if isinstance(filters, str):
		filters = json.loads(filters)

	if isinstance(item_codes, str):
		item_codes = json.loads(item_codes)

	filter_condition = get_filters_cond("Request", filters or [], [])

	item_code_condition = ""
	item_code_args = {}
	if item_codes:
		placeholders = ", ".join(["%(ic{})s".format(i) for i in range(len(item_codes))])
		item_code_condition = " AND ri.item_code IN ({})".format(placeholders)
		for i, code in enumerate(item_codes):
			item_code_args["ic{}".format(i)] = code

	events = frappe.db.sql("""
		SELECT
			`tabRequest`.name,
			`tabRequest`.company,
			`tabRequest`.department,
			ri.item_code,
			ri.unit_weight,
			`tabRequest`.posting_date as start,
			`tabRequest`.posting_date as end,
			`tabRequest`.workflow_state as status,
			1 as allDay
		FROM `tabRequest`
			INNER JOIN `tabRequest Items` ri ON ri.parent = `tabRequest`.name
		WHERE `tabRequest`.docstatus != 2
		{filter_condition}
		{item_code_condition}
		ORDER BY `tabRequest`.posting_date
	""".format(filter_condition=filter_condition, item_code_condition=item_code_condition), item_code_args, as_dict=1)

	def get_event_color(item_code):
		if not item_code:
			return {"color": "#6C757D", "textColor": "#FFFFFF"}
		prefix = item_code.upper()
		if prefix.startswith("PR-AV"):
			return {"color": "#FFC107", "textColor": "#000000"}
		if prefix.startswith("PR-LV"):
			return {"color": "#28A745", "textColor": "#FFFFFF"}
		if prefix.startswith("PR-HV"):
			return {"color": "#007BFF", "textColor": "#FFFFFF"}
		return {"color": "#6C757D", "textColor": "#FFFFFF"}

	for d in events:
		weight = " @{} Kg".format(d.unit_weight) if d.unit_weight else ""
		d.title = "{}{}".format(d.item_code or "", weight)
		d.tooltip = "{}\n{}".format(d.title, d.department or "")
		style = get_event_color(d.item_code)
		d.color = style["color"]
		d.textColor = style["textColor"]

	return events


@frappe.whitelist()
def get_request_items(filters=None):
	"""Get distinct item codes from submitted Requests with counts, for calendar card strip."""
	if isinstance(filters, str):
		filters = json.loads(filters)

	conditions = ""
	args = {}

	if filters:
		item_code = filters.get("item_code")
		if item_code and isinstance(item_code, str):
			conditions += " AND ri.item_code LIKE %(item_code)s"
			args["item_code"] = "%" + item_code + "%"

	data = frappe.db.sql("""
		SELECT
			ri.item_code,
			SUM(ri.unit_weight * ri.qty) as total_weight,
			GROUP_CONCAT(DISTINCT r.department SEPARATOR ', ') as department,
			COUNT(DISTINCT r.name) as req_count
		FROM `tabRequest Items` ri
			INNER JOIN `tabRequest` r ON r.name = ri.parent
		WHERE r.docstatus = 1
			AND YEAR(r.posting_date) = YEAR(CURDATE())
		{conditions}
		GROUP BY ri.item_code
		ORDER BY ri.item_code
	""".format(conditions=conditions), args, as_dict=1)

	return data


@frappe.whitelist()
def update_request(request_no, items, delivery_date=""):
	from erpnext.controllers.foms import sync_log
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
		items = doc.get("items", {"name":d.name})
		if items:
			item = items[0]
			item.qty = d.qty
			item.db_update()

	doc.validate()
	# doc.sync_request_so()
	doc.db_update()
	sync_log(doc, method="on_update_after_submit")
	return request_no