# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, nowtime

from erpnext.controllers.stock_controller import StockController
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.utils import get_incoming_rate
from erpnext.stock.doctype.batch.batch import get_batches


class ConsignmentOrder(DeliveryNote):
	"""Minimal Delivery Note variant for internal consignment transfer.

	This document moves stock from source warehouse to destination warehouse
	within the same company. No accounting ledger is created.
	"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# CO is not meant to update Sales Order / Sales Invoice delivery status.
		self.status_updater = []

	def before_insert(self):
		if not self.naming_series:
			self.naming_series = "CON-.YYYY.-.#####"

	def set_missing_values(self, for_validate=False):
		# Skip Delivery Note specific enrichments; keep core selling defaults.
		super(DeliveryNote, self).set_missing_values(for_validate)
		self.apply_target_warehouse_default()

	def validate(self):
		self.validate_posting_time()
		self.apply_target_warehouse_default()
		self.set_fifo_batch_numbers()
		# Run generic selling/stock/accounting validations.
		super(DeliveryNote, self).validate()

		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.update_current_stock()
		self.set_status()

	def apply_target_warehouse_default(self):
		default_source = self.get("set_warehouse")
		default_target = self.get("set_target_warehouse")
		for item in self.get("items"):
			if default_source and not item.warehouse:
				item.warehouse = default_source
			if default_target and not item.target_warehouse:
				item.target_warehouse = default_target

	def set_fifo_batch_numbers(self):
		for item in list(self.get("items")):
			if item.batch_no:
				expiry_date = frappe.db.get_value("Batch", item.batch_no, "expiry_date")
				if expiry_date and expiry_date < frappe.utils.getdate():
					item.batch_no = None
				else:
					continue
			if not item.warehouse or not item.item_code:
				continue
			if not frappe.get_cached_value("Item", item.item_code, "has_batch_no"):
				continue

			conversion_factor = flt(item.conversion_factor) or 1
			remaining_qty = flt(item.stock_qty or item.qty * conversion_factor)
			batches = get_batches(item.item_code, item.warehouse, qty=remaining_qty) or []
			allocations = []
			for batch in batches:
				batch_qty = min(flt(batch.qty), remaining_qty)
				if batch_qty <= 0:
					continue
				allocations.append((batch.batch_id, batch_qty))
				remaining_qty -= batch_qty
				if remaining_qty <= 0:
					break

			if remaining_qty > 0:
				frappe.msgprint(_("Insufficient batch stock for Item {0}").format(item.item_code))
				continue

			item.qty = allocations[0][1] / conversion_factor
			item.stock_qty = allocations[0][1]
			item.batch_no = allocations[0][0]
			row_data = item.as_dict()
			for field in ("name", "parent", "parentfield", "parenttype", "idx", "doctype"):
				row_data.pop(field, None)
			for batch_no, batch_qty in allocations[1:]:
				new_item = self.append("items", row_data.copy())
				new_item.qty = batch_qty / conversion_factor
				new_item.stock_qty = batch_qty
				new_item.batch_no = batch_no

	def validate_warehouse(self):
		# Keep standard warehouse validations (company/disabled checks).
		StockController.validate_warehouse(self)

		for d in self.get_item_list():
			is_stock_item = frappe.db.get_value("Item", d["item_code"], "is_stock_item") == 1
			if is_stock_item and not d.get("target_warehouse"):
				frappe.throw(
					_("Destination Warehouse required for stock Item {0}").format(d["item_code"])
				)

	def validate_target_warehouse(self):
		items = self.get("items") + (self.get("packed_items") or [])

		for d in items:
			if d.get("target_warehouse") and d.get("warehouse") == d.get("target_warehouse"):
				warehouse = frappe.bold(d.get("target_warehouse"))
				frappe.throw(
					_("Row {0}: Delivery Warehouse ({1}) and Customer Warehouse ({2}) can not be same").format(
						d.idx, warehouse, warehouse
					)
				)

	def update_current_stock(self):
		if self.get("_action") and self._action != "update_after_submit":
			for d in self.get("items"):
				if d.target_warehouse:
					d.actual_qty = frappe.db.get_value(
						"Bin", {"item_code": d.item_code, "warehouse": d.target_warehouse}, "actual_qty"
					)

	def update_stock_ledger(self):
		sl_entries = []
		for d in self.get_item_list():
			if frappe.get_cached_value("Item", d.item_code, "is_stock_item") == 1 and flt(d.qty):
				if flt(d.conversion_factor) == 0.0:
					d.conversion_factor = (
						get_conversion_factor(d.item_code, d.uom).get("conversion_factor") or 1.0
					)

				if not d.warehouse:
					frappe.throw(_("Source Warehouse is required in row {0}").format(d.idx))

				if not d.target_warehouse:
					frappe.throw(_("Destination Warehouse is required in row {0}").format(d.idx))

				sl_entries.append(self.get_sle_for_source_warehouse(d))
				sl_entries.append(self.get_sle_for_target_warehouse(d))

		self.make_sl_entries(sl_entries)

	def on_submit(self):
		self.update_stock_ledger()
		# Internal transfer only: no accounting ledger.
		self.repost_future_sle_and_gle()
		self.update_consignment_request_status()

	def on_cancel(self):
		super(DeliveryNote, self).on_cancel()
		self.update_stock_ledger()
		# Internal transfer only: no accounting ledger.
		self.repost_future_sle_and_gle()
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Repost Item Valuation")
		self.update_consignment_request_status()

	def update_consignment_request_status(self):
		if not self.consignment_request:
			return

		cr = frappe.get_doc("Consignment Request", self.consignment_request)

		# sync for transfer qty
		qty_map = get_qty_from_transfer(self.consignment_request)
		for d in cr.get("items"):
			key = (d.item_code, d.uom)
			if key in qty_map:
				d.transfer_qty = qty_map[key].get("qty")
			else:
				d.transfer_qty = 0

		cr.sync_qty()

def get_qty_from_transfer(con_order):
	qty_map = {}
	temp = frappe.db.sql("""
		SELECT 
			se.item_code, se.batch_no, sum(se.qty) as qty, se.uom, se.stock_uom, 
			se.conversion_factor
		FROM
			`tabConsignment Order Item` se
				LEFT JOIN
			`tabConsignment Order` s ON s.name = se.parent
		WHERE
				s.consignment_request = %s
				AND s.docstatus = 1
		group by se.item_code,  se.uom
		""", (con_order,), as_dict=1)
	
	for d in temp:
		qty_map.setdefault((d.item_code, d.uom), d)

	return qty_map