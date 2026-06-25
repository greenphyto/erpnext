# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json, erpnext
from frappe.model.document import Document
from frappe.utils import getdate, flt, cstr, add_days, today
from frappe import _
from erpnext.controllers.foms import UOM_MAP
from six import string_types
class Request(Document):
	def validate(self):
		self.calculate_price()
		self.calculate_weight()
		self.validate_date()
		self.validate_lead_time()
		self.export_salad_items()

	def on_cancel(self):
		self.detect_work_order_exists()

	def validate_date(self):
		self.posting_date = getdate(today())
		if getdate(self.delivery_date) < getdate(self.posting_date):
			frappe.throw(_("Delivery Date cannot before posting date."))

	def validate_lead_time(self):
		self.duration_days = (getdate(self.delivery_date) - getdate(self.posting_date)).days
		for d in self.get("items"):
			d.lead_time_days = frappe.get_value("Item", d.item_code, "lead_time_days") or 0
			if d.lead_time_days > 0:
				min_date = add_days(getdate(self.posting_date), d.lead_time_days)
				if getdate(self.delivery_date) < min_date:
					frappe.throw(_("Item {0} requires at least {1} days lead time. Please adjust Delivery Date accordingly.")
						.format(d.item_code, d.lead_time_days))

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

	def export_salad_items(self):
		self.salad_items = []
		for d in self.items:
			if d.is_salad_product:
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


	
	def detect_work_order_exists(self):
		data = frappe.db.sql(" select name, status, request_no from `tabWork Order` where request_no like %s and docstatus = 1", ("%" + self.name + "%",), as_dict=1)
		for d in data:
			if d.status == "Not Started":
				frappe.throw(_("Work Order {0} already exists for this request. Please cancel the work order before cancelling this request.").format(frappe.utils.get_link_to_form("Work Order", d.name)))
			else:
				frappe.throw(_("Work Order {0} for this request already in progress. Please resolve manually before cancel this request").format(frappe.utils.get_link_to_form("Work Order", d.name)))

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
def get_events(start, end, user=None, filters=None):
	"""Fetch Request events for calendar view."""
	from frappe.desk.reportview import get_filters_cond

	if isinstance(filters, str):
		filters = json.loads(filters)

	filter_condition = get_filters_cond("Request", filters or [], [])

	events = frappe.db.sql("""
		SELECT
			`tabRequest`.name,
			`tabRequest`.company,
			`tabRequest`.department,
			`tabRequest`.posting_date as start,
			`tabRequest`.posting_date as end,
			`tabRequest`.workflow_state as status,
			CONCAT(`tabRequest Items`.item_code, ' - ', IFNULL(`tabRequest`.department, '')) as title,
			1 as allDay
		FROM `tabRequest`
			LEFT JOIN `tabRequest Items` ON `tabRequest Items`.parent = `tabRequest`.name
		WHERE `tabRequest`.docstatus != 2
		{}
		ORDER BY `tabRequest`.posting_date
	""".format(filter_condition), as_dict=1)

	style_map = {
		"Draft": {"color": "#FFC107", "textColor": "#212529"},
		"Submit": {"color": "#28A745", "textColor": "#FFFFFF"},
	}

	for d in events:
		style = style_map.get(d.status)
		if style:
			d.color = style["color"]
			d.textColor = style["textColor"]

	return events


@frappe.whitelist()
def get_request_items(filters=None):
	"""Get distinct item codes from Request Items with counts, for calendar card strip."""
	if isinstance(filters, str):
		filters = json.loads(filters)

	conditions = ""
	args = {}

	if filters:
		if filters.get("item_code"):
			conditions += " AND ri.item_code LIKE %(item_code)s"
			args["item_code"] = "%" + filters["item_code"] + "%"
		if filters.get("status"):
			conditions += " AND r.workflow_state = %(status)s"
			args["status"] = filters["status"]

	data = frappe.db.sql("""
		SELECT
			ri.item_code,
			SUM(CASE WHEN r.workflow_state = 'Draft' THEN 1 ELSE 0 END) as draft_count,
			SUM(CASE WHEN r.workflow_state = 'Submit' THEN 1 ELSE 0 END) as submit_count,
			COUNT(*) as total
		FROM `tabRequest Items` ri
			INNER JOIN `tabRequest` r ON r.name = ri.parent
		WHERE r.docstatus != 2
		{conditions}
		GROUP BY ri.item_code
		ORDER BY ri.item_code
	""".format(conditions=conditions), args, as_dict=1)

	color_map = {
		"Draft": '#fd8f00',
		"Submit": '#00bf00',
	}

	for d in data:
		if d.submit_count > 0 and d.draft_count > 0:
			d.status = "Mixed"
			d.status_color = '#17A2B8'
		elif d.submit_count > 0:
			d.status = "Submit"
			d.status_color = color_map["Submit"]
		else:
			d.status = "Draft"
			d.status_color = color_map["Draft"]

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