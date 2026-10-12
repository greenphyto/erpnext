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

	def get_gl_entries(self, *args, **kwargs):
		"""Consignment Order is an internal stock transfer only — no accounting entries.
		Override prevents Repost Item Valuation from failing with
		'Cost Center is mandatory' errors when it tries to regenerate GL entries."""
		return []

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

	@frappe.whitelist()
	def fetch_batches(self):
		# Triggered by the "Get Batch" button. Runs FIFO batch allocation on the
		# in-memory doc (not saved) so the user can preview/fetch batches even
		# when the Company auto batch setting is disabled.
		self.apply_target_warehouse_default()
		self.set_fifo_batch_numbers(force=True)
		return self.as_dict()

	def apply_target_warehouse_default(self):
		default_source = self.get("set_warehouse")
		default_target = self.get("set_target_warehouse")
		for item in self.get("items"):
			if default_source and not item.warehouse:
				item.warehouse = default_source
			if default_target and not item.target_warehouse:
				item.target_warehouse = default_target

	def set_fifo_batch_numbers(self, force=False):
		# `force` is set when the user clicks the "Get Batch" button so the
		# allocation runs on demand even when the Company auto batch setting is
		# disabled. During normal validate(), it only runs if enabled.
		auto_batch_enabled = bool(
			self.company and frappe.db.get_value("Company", self.company, "enable_auto_batch")
		)
		if not auto_batch_enabled and not force:
			return

		allow_expired = auto_batch_enabled

		# Group rows that originate from the same Consignment Request line so that
		# re-running auto batch always references the ORIGINAL qty from the CR
		# (via cr_detail), not the per-row qty of an already split allocation.
		# This keeps the result stable when a line was previously split into 2-3
		# rows and later needs to shrink back (e.g. 3 rows -> 2 rows -> 1 row).
		groups = {}
		group_order = []
		for item in list(self.get("items")):
			key = item.cr_detail or f"__row__{item.name or id(item)}"
			if key not in groups:
				groups[key] = []
				group_order.append(key)
			groups[key].append(item)

		for key in group_order:
			rows = groups[key]
			anchor = rows[0]
			self._apply_fifo_for_group(anchor, rows, allow_expired, force=force)

	def _apply_fifo_for_group(self, anchor, rows, allow_expired, force=False):
		from erpnext.stock.doctype.batch.batch import get_batch_qty

		if not anchor.warehouse or not anchor.item_code:
			return
		if not frappe.get_cached_value("Item", anchor.item_code, "has_batch_no"):
			return

		conversion_factor = flt(anchor.conversion_factor) or 1

		# Always derive the required qty from the referenced Consignment Request
		# line when available; fall back to the summed row qty otherwise.
		required_qty = self._get_reference_stock_qty(anchor, conversion_factor)
		if required_qty is None:
			required_qty = sum(
				flt(r.stock_qty or flt(r.qty) * (flt(r.conversion_factor) or 1)) for r in rows
			)
		if flt(required_qty) <= 0:
			return

		# Build the full allocation plan WITHOUT mutating any row yet.
		partial_batch = None
		if anchor.batch_no:
			expiry_date = frappe.db.get_value("Batch", anchor.batch_no, "expiry_date")
			if expiry_date and expiry_date < frappe.utils.getdate() and not allow_expired:
				partial_batch = None
			elif not allow_expired and not force:
				# Auto batch disabled and not a manual trigger: keep user selection.
				return
			else:
				selected_qty = flt(get_batch_qty(batch_no=anchor.batch_no, warehouse=anchor.warehouse))
				if selected_qty >= required_qty:
					# Collapse any previous split back into the anchor row.
					self._apply_allocations(anchor, rows, [(anchor.batch_no, required_qty)], conversion_factor)
					return
				if selected_qty > 0:
					partial_batch = (anchor.batch_no, selected_qty, required_qty)

		remaining_qty = flt(required_qty)
		allocations = []
		if partial_batch:
			allocations.append((partial_batch[0], partial_batch[1]))
			remaining_qty -= partial_batch[1]

		batches = (
			get_batches(anchor.item_code, anchor.warehouse, qty=remaining_qty, allow_expired=allow_expired)
			or []
		)
		for batch in batches:
			if partial_batch and batch.batch_id == partial_batch[0]:
				continue
			batch_qty = min(flt(batch.qty), remaining_qty)
			if batch_qty <= 0:
				continue
			allocations.append((batch.batch_id, batch_qty))
			remaining_qty -= batch_qty
			if remaining_qty <= 0:
				break

		# No candidate batches cover the required qty: show a non-blocking alert
		# (toast) only, change nothing.
		if flt(remaining_qty) > 0 or not allocations:
			frappe.msgprint(
				_("Insufficient batch stock for Item {0}. Required {1}, available {2}. No changes made.").format(
					anchor.item_code,
					flt(required_qty),
					flt(required_qty) - flt(remaining_qty),
				),
				indicator="orange",
				alert=True,
			)
			return

		if partial_batch:
			frappe.msgprint(
				_("Batch {0} has only {1} qty for Item {2}. Splitting remaining qty to other batches.").format(
					frappe.bold(partial_batch[0]), partial_batch[1], anchor.item_code
				),
				indicator="orange",
				alert=True,
			)

		self._apply_allocations(anchor, rows, allocations, conversion_factor)

	def _get_reference_stock_qty(self, item, conversion_factor):
		if not item.cr_detail:
			return None
		cr_item = frappe.db.get_value(
			"Consignment Request Item",
			item.cr_detail,
			["qty", "conversion_factor", "stock_qty"],
			as_dict=True,
		)
		if not cr_item:
			return None
		cr_cf = flt(cr_item.conversion_factor) or conversion_factor or 1
		return flt(cr_item.stock_qty) or flt(cr_item.qty) * cr_cf

	def _apply_allocations(self, anchor, rows, allocations, conversion_factor):
		# Reuse the anchor row for the first allocation and drop any extra split
		# rows from a previous run so the result can grow or shrink cleanly.
		anchor.qty = allocations[0][1] / conversion_factor
		anchor.stock_qty = allocations[0][1]
		anchor.batch_no = allocations[0][0]

		row_data = anchor.as_dict()
		for field in ("name", "parent", "parentfield", "parenttype", "idx", "doctype"):
			row_data.pop(field, None)

		for extra in rows[1:]:
			self.remove(extra)

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

				if not flt(d.incoming_rate) and d.warehouse:
					d.incoming_rate = get_incoming_rate(
						{
							"item_code": d.item_code,
							"warehouse": d.warehouse,
							"posting_date": self.posting_date,
							"posting_time": self.posting_time or nowtime(),
							"qty": -1 * flt(d.qty),
							"voucher_type": self.doctype,
							"voucher_no": self.name,
							"company": self.company,
						},
						raise_error_if_no_rate=False,
					)

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
		# Reverse GL entries created during submit/repost (perpetual inventory).
		# DeliveryNote.on_cancel normally calls this, but we skip it via super().
		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Repost Item Valuation")

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