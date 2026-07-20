import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class BatchLocation(Document):
	def validate(self):
		if self.qty < 0:
			frappe.throw(_("Batch Location quantity cannot be negative."))

	def on_update(self):
		if not frappe.flags.get("warehouse_location_balance_update"):
			frappe.throw(_("Batch Location is maintained by Warehouse Action only."))


def get_batch_location_qty(batch, warehouse_location):
	return flt(
		frappe.db.get_value(
			"Batch Location",
			{"batch": batch, "warehouse_location": warehouse_location},
			"qty",
		)
		or 0
	)


def _validate_location(location_name, batch=None, receiving=False):
	location = frappe.get_doc("Warehouse Location", location_name)
	if location.disabled or location.status == "Blocked":
		frappe.throw(
			_("Warehouse Location {0} is disabled or blocked.").format(location_name)
		)
	if receiving and not location.is_mixed_storage_allowed:
		other = frappe.db.get_list(
			"Batch Location",
			filters={
				"warehouse_location": location_name,
				"qty": [">", 0],
				"batch": ["!=", batch],
			},
			fields=["name"],
			limit_page_length=1,
		)
		if other:
			frappe.throw(
				_("Warehouse Location {0} does not allow mixed storage.").format(
					location_name
				)
			)
	return location


def increase_batch_location(batch, warehouse_location, stock_qty, uom, conversion_factor):
	_validate_location(warehouse_location, batch=batch, receiving=True)
	stock_qty = flt(stock_qty)
	if stock_qty <= 0:
		frappe.throw(_("Stock quantity must be greater than zero."))
	row_name = frappe.db.get_value(
		"Batch Location",
		{"batch": batch, "warehouse_location": warehouse_location},
		"name",
	)
	if row_name:
		row = frappe.get_doc("Batch Location", row_name)
	else:
		row = frappe.new_doc("Batch Location")
		row.batch = batch
		row.warehouse_location = warehouse_location
		row.item = frappe.db.get_value("Batch", batch, "item")
		row.warehouse = frappe.db.get_value(
			"Warehouse Location", warehouse_location, "warehouse"
		)
		row.stock_uom = frappe.db.get_value("Item", row.item, "stock_uom")
	row.qty = flt(row.qty) + stock_qty
	row.uom = uom
	row.conversion_factor = conversion_factor
	row.last_updated = now_datetime()
	try:
		frappe.flags.warehouse_location_balance_update = True
		row.save(ignore_permissions=True)
	finally:
		frappe.flags.warehouse_location_balance_update = False
	return row


def decrease_batch_location(batch, warehouse_location, stock_qty):
	_validate_location(warehouse_location, batch=batch, receiving=False)
	row_name = frappe.db.get_value(
		"Batch Location",
		{"batch": batch, "warehouse_location": warehouse_location},
		"name",
	)
	current_qty = get_batch_location_qty(batch, warehouse_location)
	if not row_name or current_qty < flt(stock_qty):
		frappe.throw(
			_("Insufficient quantity for Batch {0} at Warehouse Location {1}.").format(
				batch, warehouse_location
			)
		)
	row = frappe.get_doc("Batch Location", row_name)
	row.qty = current_qty - flt(stock_qty)
	row.last_updated = now_datetime()
	try:
		frappe.flags.warehouse_location_balance_update = True
		if row.qty == 0:
			row.delete(ignore_permissions=True)
		else:
			row.save(ignore_permissions=True)
	finally:
		frappe.flags.warehouse_location_balance_update = False
