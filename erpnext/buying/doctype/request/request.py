# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe, json, erpnext
from frappe.model.document import Document
from frappe.utils import getdate, flt, cstr, cint, today
from frappe import _
from erpnext.controllers.foms import UOM_MAP
from erpnext.stock.get_item_details import get_item_price
from six import string_types
import csv
from io import StringIO

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



def _get_forecast_settings():
	"""Get Forecast Settings with mapping tables."""
	settings = frappe.get_doc("Forecast Settings", "Forecast Settings")
	if not settings.enable:
		frappe.throw(_("Forecast Settings is not enabled"))
	return settings


def get_lead_time_by_custom_names(custom_names):
	"""
	Get lead time for items by custom names from Forecast Settings.

	Args:
		custom_names: List of custom names (e.g., ["Kai Lan", "Komatsuna"])

	Returns:
		dict with min_lead_time, max_lead_time, and detail
	"""
	if isinstance(custom_names, string_types):
		custom_names = json.loads(custom_names)

	settings = _get_forecast_settings()
	detail = {}

	for custom_name in custom_names:
		item_code = _resolve_item(custom_name, settings)
		if item_code:
			lead_time = frappe.get_value("Item", item_code, "lead_time_days") or 0
			detail[custom_name] = lead_time
		else:
			detail[custom_name] = None

	# Calculate min/max from values that are not None
	lead_times = [v for v in detail.values() if v is not None]

	return {
		"min_lead_time": min(lead_times) if lead_times else 0,
		"max_lead_time": max(lead_times) if lead_times else 0,
		"detail": detail
	}


def _resolve_item(veg_name, settings):
	"""Map custom_name to item_code from Forecast Settings items table."""
	for row in settings.items:
		if row.custom_name == veg_name and row.ref_doctype == "Item":
			return row.ref_name
	return None


def _resolve_customer(customer_name, settings):
	"""Map custom_name to customer from Forecast Settings customers table."""
	for row in settings.customers:
		if row.custom_name == customer_name and row.ref_doctype == "Customer":
			return row.ref_name
	return None


def _resolve_packaging(item_code, uom_in_kg):
	"""Find packaging by weight from Item's packaging_list_available table."""
	packaging = frappe.get_all(
		"Packaging List Available",
		filters={"parent": item_code, "weight": flt(uom_in_kg)},
		fields=["package_item", "uom"],
		limit=1
	)
	if packaging:
		return packaging[0]
	return None


def _get_item_price(item_code):
	"""Get rate from Item Price for default selling price list."""
	price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
	if not price_list:
		price_list = frappe.db.get_single_value("Stock Settings", "default_price_list")

	if not price_list:
		return 0

	args = {
		"price_list": price_list,
		"uom": "",
		"batch_no": ""
	}
	prices = get_item_price(args, item_code)
	if prices:
		return prices[0][1]  # price_list_rate
	return 0


def _get_existing_request(customer, delivery_date):
	"""Check for existing draft Request with same customer and delivery date."""
	name = frappe.db.exists(
		"Request",
		{
			"proposed_customer": customer,
			"delivery_date": delivery_date,
			"docstatus": 0
		}
	)
	if name:
		return frappe.get_doc("Request", name)
	return None


def _add_item_to_request(doc, item_data):
	"""Add or update item in Request. Replace qty if item_code exists.
	Returns dict with change info: {action: 'new'|'qty_changed'|'no_change', row_idx, old_qty, new_qty}
	"""
	existing_items = doc.get("items", {"item_code": item_data["item_code"]})
	if existing_items:
		# Update existing item
		item = existing_items[0]
		old_qty = flt(item.qty)
		new_qty = flt(item_data["qty"])
		item.qty = new_qty
		item.uom = item_data["uom"]
		item.packaging_item = item_data["packaging_item"]
		item.rate = item_data["rate"]
		if old_qty != new_qty:
			return {"action": "qty_changed", "item_code": item_data["item_code"],
					"row_idx": item.idx, "old_qty": old_qty, "new_qty": new_qty}
		return {"action": "no_change"}
	else:
		# Add new item
		row = doc.append("items")
		row.item_code = item_data["item_code"]
		row.qty = item_data["qty"]
		row.uom = item_data["uom"]
		row.packaging_item = item_data["packaging_item"]
		row.rate = item_data["rate"]
		return {"action": "new", "item_code": item_data["item_code"], "row_idx": row.idx}


def create_or_update_forecast_request(items, customer_name, forecast_date, settings):
	"""
	Create or update Request for forecast items.

	Args:
		items: List of mapped item data
		customer_name: Customer name (from mapping)
		forecast_date: Delivery date
		settings: Forecast Settings document

	Returns:
		dict with request_name and item results
	"""
	# Check for existing Request
	doc = _get_existing_request(customer_name, forecast_date)

	if not doc:
		# Create new Request
		doc = frappe.new_doc("Request")
		doc.company = settings.company_default or erpnext.get_default_company()
		doc.department = settings.department_default
		doc.posting_date = getdate(today())
		doc.delivery_date = getdate(forecast_date)
		doc.proposed_customer = customer_name
		doc.workflow_state = "Draft"

	# Process each item
	item_results = []
	changes = []
	for item in items:
		try:
			change = _add_item_to_request(doc, item)
			if change:
				changes.append(change)
			item_results.append({
				"veg_name": item.get("veg_name", ""),
				"status": "success",
				"item_code": item["item_code"]
			})
		except Exception as e:
			item_results.append({
				"veg_name": item.get("veg_name", ""),
				"status": "failed",
				"error": str(e)
			})

	# Save document
	is_new = not doc.name
	if is_new:
		doc.insert(ignore_permissions=1)
	else:
		doc.save(ignore_permissions=1)

	# Add comment only if there are changes
	has_new_items = any(c.get("action") == "new" for c in changes)
	has_qty_changes = any(c.get("action") == "qty_changed" for c in changes)

	if is_new:
		doc.add_comment(
			"Comment",
			"Created via Forecast API. Processed {0} items.".format(len(items))
		)
	elif has_new_items or has_qty_changes:
		msg_parts = []
		for c in changes:
			if c["action"] == "new":
				msg_parts.append("Added {0} (row {1})".format(c["item_code"], c["row_idx"]))
			elif c["action"] == "qty_changed":
				msg_parts.append("{0} (row {1}) qty {2} → {3}".format(
					c["item_code"], c["row_idx"], c["old_qty"], c["new_qty"]))
		doc.add_comment(
			"Comment",
			"Updated via Forecast API: " + "; ".join(msg_parts)
		)

	success_count = len([r for r in item_results if r["status"] == "success"])
	return {
		"request_name": doc.name,
		"items_processed": len(items),
		"items_success": success_count,
		"items_failed": len(items) - success_count,
		"details": item_results
	}


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
			ROUND(ri.unit_weight * 1000) as package_size,
			`tabRequest`.delivery_date as start,
			`tabRequest`.delivery_date as end,
			`tabRequest`.workflow_state as status,
			`tabRequest`.docstatus,
			1 as allDay
		FROM `tabRequest`
			INNER JOIN `tabRequest Items` ri ON ri.parent = `tabRequest`.name
		WHERE `tabRequest`.docstatus != 2
		{filter_condition}
		{item_code_condition}
		ORDER BY `tabRequest`.posting_date
	""".format(filter_condition=filter_condition, item_code_condition=item_code_condition), item_code_args, as_dict=1)

	def get_event_color(item_code, docstatus):
		is_draft = (docstatus == 0)
		if not item_code:
			return {"color": "#6C757D", "textColor": "#FFFFFF"}
		prefix = item_code.upper()
		if prefix.startswith("PR-AV"):
			return {"color": "#FFC107" if not is_draft else "#EC008C", "textColor": "#000000" if not is_draft else "#FFFFFF"}
		if prefix.startswith("PR-LV"):
			return {"color": "#28A745" if not is_draft else "#00FFFF", "textColor": "#FFFFFF" if not is_draft else "#000000"}
		if prefix.startswith("PR-HV"):
			return {"color": "#007BFF" if not is_draft else "#934FA7", "textColor": "#FFFFFF"}
		return {"color": "#6C757D", "textColor": "#FFFFFF"}

	for d in events:
		weight = " #{} Kg".format(d.unit_weight) if d.unit_weight else ""
		d.title = "{}{}".format(d.item_code or "", weight)
		d.package_size = "@{} Gr".format(cint(d.package_size)) if d.package_size else ""
		d.tooltip = "{}\n{}".format(d.title, d.department or "")
		style = get_event_color(d.item_code, d.docstatus)
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
			i.item_name,
			SUM(ri.unit_weight * ri.qty) as total_weight,
			GROUP_CONCAT(DISTINCT r.department SEPARATOR ', ') as department,
			GROUP_CONCAT(DISTINCT ri.uom SEPARATOR ', ') as package_size,
			COUNT(DISTINCT r.name) as req_count
		FROM `tabRequest Items` ri
			INNER JOIN `tabRequest` r ON r.name = ri.parent
			LEFT JOIN `tabItem` i ON i.name = ri.item_code
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


@frappe.whitelist()
def fetch_tray_data(item_codes):
	"""Fetch tray config from FOMS for given item codes"""
	from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI

	if isinstance(item_codes, string_types):
		item_codes = json.loads(item_codes)

	api = FomsAPI()
	tray_data_list = []

	for item_code in item_codes:
		foms_product_id = frappe.get_value("Item", item_code, "foms_product_id")
		if not foms_product_id:
			continue

		config = api.get_max_cage_and_tray(foms_product_id)
		if not config:
			continue

		config["item_code"] = item_code
		tray_data_list.append(config)

	return tray_data_list


@frappe.whitelist()
def generate_tray_data_html(tray_data_list):
	"""Generate HTML table from tray data"""
	if isinstance(tray_data_list, string_types):
		tray_data_list = json.loads(tray_data_list)
	if not tray_data_list:
		return "<p>No tray data available</p>"

	html = """
	<style>
		.tray-data-wrapper {
			overflow-x: auto;
			max-width: 100%;
		}
		.tray-data-table {
			width: 100%;
			min-width: 800px;
			border-collapse: collapse;
			font-size: 12px;
		}
		.tray-data-table th, .tray-data-table td {
			border: 1px solid #d1d8dd;
			padding: 6px 8px;
			text-align: left;
			white-space: nowrap;
		}
		.tray-data-table th {
			background-color: #f5f7fa;
			font-weight: 600;
		}
		.tray-data-table tr:nth-child(even) {
			background-color: #fafbfc;
		}
		.tray-data-table th:first-child,
		.tray-data-table td:first-child {
			min-width: 100px;
		}
	</style>
	<div class="tray-data-wrapper">
	<table class="tray-data-table">
		<thead>
			<tr>
				<th>Item Code</th>
				<th>Product ID</th>
				<th>Product Name</th>
				<th>Weight/Plant (Kg)</th>
				<th>Packet Size (g)</th>
				<th>Seeding Plant/Tray</th>
				<th>Seeding Tray/Cage</th>
				<th>Max Pkt/Seeding Tray</th>
				<th>Max Pkt/Seeding Cage</th>
				<th>Transplant Plant/Tray</th>
				<th>Transplant Tray/Cage</th>
				<th>Max Pkt/Transplant Tray</th>
				<th>Max Pkt/Transplant Cage</th>
			</tr>
		</thead>
		<tbody>
	"""

	for data in tray_data_list:
		html += """
			<tr>
				<td>{item_code}</td>
				<td>{productId}</td>
				<td>{productName}</td>
				<td>{weightPerPlantKg}</td>
				<td>{packetSizeGrams}</td>
				<td>{seedingPlantPerTray}</td>
				<td>{seedingTraysPerCage}</td>
				<td>{maxPacketsPerSeedingTray}</td>
				<td>{maxPacketsPerSeedingCage}</td>
				<td>{transplantingPlantPerTray}</td>
				<td>{transplantingTraysPerCage}</td>
				<td>{maxPacketsPerTransplantingTray}</td>
				<td>{maxPacketsPerTransplantingCage}</td>
			</tr>
		""".format(
			item_code=data.get("item_code", ""),
			productId=data.get("productId", ""),
			productName=data.get("productName", ""),
			weightPerPlantKg=data.get("weightPerPlantKg", ""),
			packetSizeGrams=data.get("packetSizeGrams", ""),
			seedingPlantPerTray=data.get("seedingPlantPerTray", ""),
			seedingTraysPerCage=data.get("seedingTraysPerCage", ""),
			maxPacketsPerSeedingTray=data.get("maxPacketsPerSeedingTray", ""),
			maxPacketsPerSeedingCage=data.get("maxPacketsPerSeedingCage", ""),
			transplantingPlantPerTray=data.get("transplantingPlantPerTray", ""),
			transplantingTraysPerCage=data.get("transplantingTraysPerCage", ""),
			maxPacketsPerTransplantingTray=data.get("maxPacketsPerTransplantingTray", ""),
			maxPacketsPerTransplantingCage=data.get("maxPacketsPerTransplantingCage", "")
		)

	html += """
		</tbody>
	</table>
	</div>
	"""

	return html


@frappe.whitelist()
def parse_forecast_upload(csv_content):
	"""Parse forecast CSV content, map items, and group by (delivery_date, customer).

	Args:
		csv_content: Raw CSV string content

	Returns:
		dict with groups, warnings, and summary
	"""
	if not csv_content or not csv_content.strip():
		frappe.throw(_("CSV content is empty"))

	settings = _get_forecast_settings()

	reader = csv.DictReader(StringIO(csv_content))

	# Validate required columns
	required_columns = ["Delivery Date", "Customer", "Vegetable", "Predicted Packages", "UOM (kg)", "Unit Price (SGD)"]
	if not reader.fieldnames:
		frappe.throw(_("Invalid CSV format: no header row found"))

	missing = [col for col in required_columns if col not in reader.fieldnames]
	if missing:
		frappe.throw(_("Missing required columns: {0}").format(", ".join(missing)))

	groups_dict = {}  # {(delivery_date, customer): {items: [...]}}
	warnings = []
	row_num = 1  # header is row 0

	for row in reader:
		row_num += 1
		delivery_date = row.get("Delivery Date", "").strip()
		customer = row.get("Customer", "").strip()
		vegetable = row.get("Vegetable", "").strip()
		predicted_packages = row.get("Predicted Packages", "").strip()
		uom_kg = row.get("UOM (kg)", "").strip()
		unit_price = row.get("Unit Price (SGD)", "").strip()

		if not delivery_date or not customer or not vegetable:
			continue

		# Validate delivery date format
		try:
			getdate(delivery_date)
		except Exception:
			warnings.append({
				"row": row_num,
				"message": "Invalid delivery date '{0}' (row {1})".format(delivery_date, row_num)
			})
			continue

		# Resolve customer name via Forecast Settings
		resolved_customer = _resolve_customer(customer, settings)
		if not resolved_customer:
			warnings.append({
				"row": row_num,
				"message": "Customer '{0}' not found in Forecast Settings (row {1})".format(customer, row_num)
			})
			continue
		customer = resolved_customer

		# Map vegetable to item_code via Forecast Settings
		item_code = _resolve_item(vegetable, settings)
		if not item_code:
			warnings.append({
				"row": row_num,
				"message": "Vegetable '{0}' not found in Forecast Settings (row {1})".format(vegetable, row_num)
			})
			continue

		# Resolve packaging from item
		packaging = _resolve_packaging(item_code, flt(uom_kg)) if uom_kg else None
		packaging_display = ""
		packaging_item = ""
		uom = ""
		if packaging:
			packaging_item = packaging.get("package_item", "")
			uom = packaging.get("uom", "")
			# Build display string like "200 Gr" from weight in kg
			weight_grams = flt(uom_kg) * 1000
			packaging_display = "{0:g} Gr".format(weight_grams)
		else:
			# Fallback: build from csv weight
			if uom_kg:
				weight_grams = flt(uom_kg) * 1000
				packaging_display = "{0:g} Gr".format(weight_grams)
			warnings.append({
				"row": row_num,
				"message": "No packaging found for {0} with weight {1} kg (row {2})".format(item_code, uom_kg, row_num)
			})

		# Get rate from Item Price
		rate = _get_item_price(item_code)
		if not rate and unit_price:
			rate = flt(unit_price)

		qty = flt(predicted_packages) if predicted_packages else 0
		if not qty:
			warnings.append({
				"row": row_num,
				"message": "Missing or zero Predicted Packages for '{0}' (row {1})".format(vegetable, row_num)
			})
			continue

		unit_weight = flt(uom_kg) if uom_kg else 0
		total_kg = qty * unit_weight

		item_data = {
			"vegetable": vegetable,
			"item_code": item_code,
			"qty": qty,
			"uom": uom,
			"packaging": packaging_display,
			"packaging_item": packaging_item,
			"rate": rate,
			"unit_weight": unit_weight,
			"total_kg": round(total_kg, 2),
			"warning": None,
		}

		# Add warning flag if packaging was missing
		if not packaging:
			item_data["warning"] = "No packaging found"

		group_key = (delivery_date, customer)
		if group_key not in groups_dict:
			groups_dict[group_key] = {
				"delivery_date": delivery_date,
				"customer": customer,
				"items": []
			}
		groups_dict[group_key]["items"].append(item_data)

	# Convert to list preserving order
	groups = list(groups_dict.values())

	total_items = sum(len(g["items"]) for g in groups)

	return {
		"groups": groups,
		"warnings": warnings,
		"summary": {
			"total_groups": len(groups),
			"total_items": total_items
		}
	}

@frappe.whitelist()
def generate_bulk_requests(groups, edits=None):
	"""Generate Request drafts from grouped forecast data.

	Args:
	    groups: JSON string or list of {delivery_date, customer, items: [...]}
	    edits: JSON string or dict of {group_idx: {item_idx: {qty: new_qty}}}

	Returns:
	    dict with created, merged, errors, and summary
	"""
	if isinstance(groups, string_types):
		groups = json.loads(groups)

	if isinstance(edits, string_types):
		edits = json.loads(edits)

	if not edits:
		edits = {}

	if not groups:
		frappe.throw(_("No groups provided for bulk upload"))

	settings = _get_forecast_settings()
	created = []
	merged = []
	errors = []

	for idx, group in enumerate(groups):
		delivery_date = group.get("delivery_date")
		customer = group.get("customer")
		items = group.get("items", [])

		group_label = "{0} - {1}".format(delivery_date, customer)

		if not items:
			errors.append({"group": group_label, "error": "No items in group"})
			continue

		# Apply edits to qty
		group_edits = edits.get(str(idx), {})
		for item_idx, item in enumerate(items):
			item_edit = group_edits.get(str(item_idx), {})
			if "qty" in item_edit:
				item["qty"] = flt(item_edit["qty"])

		# Check for existing draft Request
		doc = _get_existing_request(customer, delivery_date)

		is_new = not doc
		if is_new:
			doc = frappe.new_doc("Request")
			doc.company = settings.company_default or erpnext.get_default_company()
			doc.department = settings.department_default
			doc.posting_date = getdate(today())
			doc.delivery_date = getdate(delivery_date)
			doc.proposed_customer = customer
			doc.workflow_state = "Draft"

		added_items = []
		for item in items:
			try:
				change = _add_item_to_request(doc, item)
				if change and change.get("action") in ("new", "qty_changed"):
					added_items.append(item["item_code"])
			except Exception as e:
				frappe.log_error(
					title="Bulk Request Generation Error",
					message="Group {0}, Item {1}: {2}".format(group_label, item.get("item_code", "?"), str(e))
				)
				errors.append({
					"group": group_label,
					"error": "Item {0}: {1}".format(item.get("item_code", "?"), str(e))
				})

		if not added_items:
			if not is_new:
				# Existing doc, nothing changed
				continue
			# All items failed for new doc; don't create empty Request
			continue

		try:
			if is_new:
				doc.insert(ignore_permissions=1)
				created.append(doc.name)
				doc.add_comment(
					"Comment",
					"Created via Bulk Upload. {0} items.".format(len(added_items))
				)
			else:
				doc.save(ignore_permissions=1)
				merged.append({
					"name": doc.name,
					"added_items": added_items
				})
				doc.add_comment(
					"Comment",
					"Updated via Bulk Upload: " + ", ".join(added_items)
				)
		except Exception as e:
			frappe.log_error(
				title="Bulk Request Generation Error",
				message="Group {0}, Save failed: {1}".format(group_label, str(e))
			)
			errors.append({
				"group": group_label,
				"error": "Save failed: {0}".format(str(e))
			})

	summary_parts = []
	if created:
		summary_parts.append("{0} created".format(len(created)))
	if merged:
		summary_parts.append("{0} merged".format(len(merged)))
	if errors:
		summary_parts.append("{0} errors".format(len(errors)))

	return {
		"created": created,
		"merged": merged,
		"errors": errors,
		"summary": ", ".join(summary_parts) if summary_parts else "No changes"
	}
