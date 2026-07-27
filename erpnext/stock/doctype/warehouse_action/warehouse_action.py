import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from erpnext.stock.doctype.batch_location.batch_location import (
	decrease_batch_location,
	increase_batch_location,
)
from erpnext.stock.doctype.warehouse_location_settings.warehouse_location_settings import (
	get_default_warehouse,
)


class WarehouseAction(Document):
	def before_validate(self):
		if not self.user or self.user == "frappe.session.user":
			self.user = frappe.session.user
		self.posting_datetime = self.posting_datetime or now_datetime()
		self.item = frappe.db.get_value("Batch", self.batch, "item")
		self.warehouse = get_default_warehouse()
		self.stock_uom = frappe.db.get_value("Item", self.item, "stock_uom")
		self.stock_qty = flt(self.qty) * flt(self.conversion_factor)

	def validate(self):
		if self.qty <= 0:
			frappe.throw(_("Quantity must be greater than zero."))
		if self.conversion_factor <= 0:
			frappe.throw(_("Conversion Factor must be greater than zero."))
		if self.action_type in ("New", "Move") and not self.to_location:
			frappe.throw(_("Target Warehouse Location is required for {0}.").format(self.action_type))
		if self.action_type in ("Move", "Discard") and not self.from_location:
			frappe.throw(_("Source Warehouse Location is required for {0}.").format(self.action_type))
		if self.action_type == "Move" and self.from_location == self.to_location:
			frappe.throw(_("Source and Target Warehouse Location must be different."))
		self.validate_locations()

	def validate_locations(self):
		for location_name in filter(None, (self.from_location, self.to_location)):
			location_warehouse = frappe.db.get_value("Warehouse Location", location_name, "warehouse")
			if location_warehouse != self.warehouse:
				frappe.throw(
					_("Warehouse Location {0} is outside the configured Default Warehouse.").format(
						location_name
					)
				)
			location = frappe.get_doc("Warehouse Location", location_name)
			if location.disabled or location.status == "Blocked":
				frappe.throw(
					_("Warehouse Location {0} is disabled or blocked.").format(location_name)
				)

	def on_submit(self):
		if self.action_type == "New":
			increase_batch_location(
				self.batch, self.to_location, self.stock_qty, self.uom, self.conversion_factor
			)
		elif self.action_type == "Move":
			decrease_batch_location(self.batch, self.from_location, self.stock_qty)
			try:
				increase_batch_location(
					self.batch, self.to_location, self.stock_qty, self.uom, self.conversion_factor
				)
			except Exception:
				increase_batch_location(
					self.batch, self.from_location, self.stock_qty, self.uom, self.conversion_factor
				)
				raise
		else:
			decrease_batch_location(self.batch, self.from_location, self.stock_qty)

	def on_cancel(self):
		if self.action_type == "New":
			decrease_batch_location(self.batch, self.to_location, self.stock_qty)
		elif self.action_type == "Move":
			decrease_batch_location(self.batch, self.to_location, self.stock_qty)
			try:
				increase_batch_location(
					self.batch, self.from_location, self.stock_qty, self.uom, self.conversion_factor
				)
			except Exception:
				increase_batch_location(
					self.batch, self.to_location, self.stock_qty, self.uom, self.conversion_factor
				)
				raise
		else:
			increase_batch_location(
				self.batch, self.from_location, self.stock_qty, self.uom, self.conversion_factor
			)


@frappe.whitelist()
def get_action_context():
	warehouse = get_default_warehouse()
	return {
		"warehouse": warehouse,
		"warehouse_code": frappe.db.get_value("Warehouse", warehouse, "warehouse_code"),
	}


@frappe.whitelist()
def get_batch_source_locations(batch, warehouse=None):
	default_warehouse = get_default_warehouse()
	if warehouse and warehouse != default_warehouse:
		frappe.throw(_("Warehouse must match the configured Default Warehouse."))
	if not batch or not default_warehouse:
		return []

	bl = frappe.qb.DocType("Batch Location")
	wl = frappe.qb.DocType("Warehouse Location")
	batch_dt = frappe.qb.DocType("Batch")
	return (
		frappe.qb.from_(bl)
		.join(wl)
		.on(bl.warehouse_location == wl.name)
		.left_join(batch_dt)
		.on(bl.batch == batch_dt.name)
		.select(
			bl.batch,
			batch_dt.expiry_date,
			bl.warehouse_location,
			bl.qty,
			bl.stock_uom,
			wl.aisle_row,
			wl.bay_column,
			wl.level_tier,
		)
		.where(bl.batch == batch)
		.where(bl.warehouse == default_warehouse)
		.where(bl.qty > 0)
		.orderby(batch_dt.expiry_date)
		.orderby(bl.warehouse_location)
		.run(as_dict=True)
	)


@frappe.whitelist()
def get_item_source_locations(item, warehouse=None):
	"""All batch locations for item, FIFO by earliest expiry date first."""
	default_warehouse = get_default_warehouse()
	if warehouse and warehouse != default_warehouse:
		frappe.throw(_("Warehouse must match the configured Default Warehouse."))
	if not item or not default_warehouse:
		return []

	bl = frappe.qb.DocType("Batch Location")
	batch_dt = frappe.qb.DocType("Batch")
	return (
		frappe.qb.from_(bl)
		.left_join(batch_dt)
		.on(bl.batch == batch_dt.name)
		.select(
			bl.batch,
			batch_dt.expiry_date,
			bl.warehouse_location,
			bl.qty,
			bl.stock_uom,
		)
		.where(bl.item == item)
		.where(bl.warehouse == default_warehouse)
		.where(bl.qty > 0)
		.orderby(batch_dt.expiry_date)
		.orderby(bl.batch)
		.orderby(bl.warehouse_location)
		.run(as_dict=True)
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def batch_location_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	batch = filters.get("batch")
	warehouse = filters.get("warehouse") or get_default_warehouse()
	if not batch or not warehouse:
		return []

	batch_location_filters = {
		"batch": batch,
		"warehouse": warehouse,
		"qty": [">", 0],
	}
	if txt:
		batch_location_filters["warehouse_location"] = ["like", "%{}%".format(txt)]

	return frappe.db.get_list(
		"Batch Location",
		filters=batch_location_filters,
		fields=["warehouse_location as name"],
		order_by="warehouse_location asc",
		start=start,
		page_length=page_len,
		as_list=not as_dict,
	)


@frappe.whitelist()
def get_batch_location_stock(batch, warehouse_location):
	default_warehouse = get_default_warehouse()
	if not batch or not warehouse_location or not default_warehouse:
		return {"qty": 0, "stock_uom": ""}

	return frappe.db.get_value(
		"Batch Location",
		{
			"batch": batch,
			"warehouse_location": warehouse_location,
			"warehouse": default_warehouse,
		},
		["qty", "stock_uom"],
		as_dict=True,
	) or {"qty": 0, "stock_uom": ""}
