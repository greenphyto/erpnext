# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.controllers.stock_controller import StockController
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.utils import get_incoming_rate


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

	def get_item_valuation_warehouse(self, item_row):
		if item_row.get("warehouse"):
			return item_row.warehouse

		if self.get("set_warehouse"):
			return self.set_warehouse

		if self.get("consignment_request"):
			request_warehouse = frappe.db.get_value(
				"Consignment Request", self.consignment_request, "set_warehouse"
			)
			if request_warehouse:
				return request_warehouse

		if item_row.get("batch_no"):
			rows = frappe.db.sql(
				"""
				select warehouse
				from `tabStock Ledger Entry`
				where item_code = %s
					and batch_no = %s
					and warehouse != %s
					and is_cancelled = 0
				order by timestamp(posting_date, posting_time) desc, creation desc
				limit 1
				""",
				(item_row.item_code, item_row.batch_no, item_row.target_warehouse or ""),
			)
			if rows:
				return rows[0][0]

		return None

	def get_consignment_incoming_rate(self, item_row, qty=None):
		valuation_warehouse = self.get_item_valuation_warehouse(item_row)
		if not valuation_warehouse:
			return 0

		stock_qty = flt(qty if qty is not None else item_row.get("stock_qty"))
		if not stock_qty and flt(item_row.get("qty")):
			stock_qty = flt(item_row.qty) * flt(item_row.conversion_factor or 1)

		if not stock_qty:
			return 0

		args = frappe._dict(
			{
				"item_code": item_row.item_code,
				"warehouse": valuation_warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"qty": stock_qty,
				"serial_no": item_row.get("serial_no"),
				"batch_no": item_row.get("batch_no"),
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"company": self.company,
			}
		)

		return flt(get_incoming_rate(args, raise_error_if_no_rate=False))

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

				d.incoming_rate = self.get_consignment_incoming_rate(d)

				sl_entries.append(self.get_sle_for_target_warehouse(d))

		self.make_sl_entries(sl_entries)

	def get_stock_ledger_details(self, from_partial_return=False, only_for_item=[]):
		sle_map = super().get_stock_ledger_details(
			from_partial_return=from_partial_return, only_for_item=only_for_item
		)

		item_map = {item.name: item for item in self.get("items")}
		for voucher_detail_no, sle_list in sle_map.items():
			item_row = item_map.get(voucher_detail_no)
			if not item_row:
				continue

			for sle in sle_list:
				if flt(sle.stock_value_difference):
					continue

				incoming_rate = self.get_consignment_incoming_rate(item_row, qty=abs(flt(sle.actual_qty)))
				if not incoming_rate:
					continue

				sle.valuation_rate = incoming_rate
				sle.incoming_rate = incoming_rate
				sle.stock_value_difference = flt(sle.actual_qty) * incoming_rate

		return sle_map

	def on_submit(self):
		# super(ConsignmentOrder, self).on_submit()
		self.update_stock_ledger()
		self.make_gl_entries()
		self.repost_future_sle_and_gle()
		self.update_consignment_request_status()

	def on_cancel(self):
		super(ConsignmentOrder, self).on_cancel()
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Repost Item Valuation")

	def update_consignment_request_status(self):
		# No linked Consignment Request, so skip status updates.
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