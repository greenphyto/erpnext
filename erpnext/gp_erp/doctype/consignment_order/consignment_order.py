# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.controllers.stock_controller import StockController
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
from erpnext.stock.get_item_details import get_conversion_factor


class ConsignmentOrder(DeliveryNote):
	"""Minimal Delivery Note variant for consignment inbound flow.

	This document only posts stock into destination warehouse (`target_warehouse`).
	No source-warehouse issue, return/replacement workflow, or SO/SI status sync.
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
		# Run generic selling/stock/accounting validations.
		super(DeliveryNote, self).validate()

		self.apply_target_warehouse_default()
		self.validate_warehouse()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.update_current_stock()
		self.set_status()
		self.reset_default_field_value("set_target_warehouse", "items", "target_warehouse")

	def apply_target_warehouse_default(self):
		default_target = self.get("set_target_warehouse")
		for item in self.get("items"):
			if default_target and not item.target_warehouse:
				item.target_warehouse = default_target
			# Force CO to only move stock into destination warehouse.
			item.warehouse = ""

	def validate_warehouse(self):
		# Keep standard warehouse validations (company/disabled checks).
		StockController.validate_warehouse(self)

		for d in self.get_item_list():
			is_stock_item = frappe.db.get_value("Item", d["item_code"], "is_stock_item") == 1
			if is_stock_item and not d.get("target_warehouse"):
				frappe.throw(
					_("Destination Warehouse required for stock Item {0}").format(d["item_code"])
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

				if not d.target_warehouse:
					frappe.throw(_("Destination Warehouse is required in row {0}").format(d.idx))

				sl_entries.append(self.get_sle_for_target_warehouse(d))

		self.make_sl_entries(sl_entries)

	def on_submit(self):
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()

	def on_cancel(self):
		super(DeliveryNote, self).on_cancel()
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Repost Item Valuation")
