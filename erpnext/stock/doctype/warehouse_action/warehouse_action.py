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

	return frappe.db.get_list(
		"Batch Location",
		filters={
			"batch": batch,
			"warehouse": default_warehouse,
			"qty": [">", 0],
		},
		fields=["warehouse_location", "qty", "stock_uom"],
		order_by="qty desc",
		limit_page_length=0,
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
