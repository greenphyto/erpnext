# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt
from frappe.tests.utils import FrappeTestCase

from erpnext.gp_erp.doctype.consignment_order import consignment_order as co_module


class FakeBatch(frappe._dict):
	pass


def make_doc(rows, cr_stock_qty_map):
	"""Build an in-memory Consignment Order-like object exercising the grouping
	logic without touching the database."""
	doc = frappe.new_doc("Consignment Order")
	doc.company = None
	for r in rows:
		doc.append("items", r)

	# Stub reference lookup: cr_detail -> required stock qty from CR.
	doc._get_reference_stock_qty = lambda item, cf, _m=cr_stock_qty_map: _m.get(item.cr_detail)
	return doc


class TestConsignmentOrderAutoBatch(FrappeTestCase):
	def setUp(self):
		self._orig_get_batches = co_module.get_batches
		self._item_has_batch = frappe.get_cached_value

	def tearDown(self):
		co_module.get_batches = self._orig_get_batches
		frappe.get_cached_value = self._item_has_batch

	def _patch(self, available, has_batch=True):
		co_module.get_batches = lambda item_code, warehouse, qty=None, allow_expired=False: [
			FakeBatch({"batch_id": b, "qty": q}) for b, q in available
		]
		frappe.get_cached_value = lambda dt, dn, field, *a, **k: (
			1 if field == "has_batch_no" and has_batch else self._item_has_batch(dt, dn, field, *a, **k)
		)

	def test_shrink_three_rows_to_one(self):
		# Previously split into 3 rows; now one batch covers the full CR qty.
		rows = [
			{"item_code": "IT", "warehouse": "WH", "cr_detail": "CR1", "conversion_factor": 1, "qty": 4, "stock_qty": 4},
			{"item_code": "IT", "warehouse": "WH", "cr_detail": "CR1", "conversion_factor": 1, "qty": 4, "stock_qty": 4},
			{"item_code": "IT", "warehouse": "WH", "cr_detail": "CR1", "conversion_factor": 1, "qty": 4, "stock_qty": 4},
		]
		doc = make_doc(rows, {"CR1": 12})
		self._patch(available=[("B1", 100)])
		doc.set_fifo_batch_numbers(force=True)
		items = doc.get("items")
		self.assertEqual(len(items), 1)
		self.assertEqual(flt(items[0].stock_qty), 12)
		self.assertEqual(items[0].batch_no, "B1")

	def test_split_one_row_to_two(self):
		# Single row referencing CR qty 12; stock spread across two batches.
		rows = [
			{"item_code": "IT", "warehouse": "WH", "cr_detail": "CR1", "conversion_factor": 1, "qty": 12, "stock_qty": 12},
		]
		doc = make_doc(rows, {"CR1": 12})
		self._patch(available=[("B1", 5), ("B2", 20)])
		doc.set_fifo_batch_numbers(force=True)
		items = doc.get("items")
		self.assertEqual(len(items), 2)
		self.assertEqual({i.batch_no for i in items}, {"B1", "B2"})
		self.assertEqual(sum(flt(i.stock_qty) for i in items), 12)

	def test_insufficient_leaves_rows_untouched(self):
		# Candidate batches cannot cover CR qty: nothing changes.
		rows = [
			{"item_code": "IT", "warehouse": "WH", "cr_detail": "CR1", "conversion_factor": 1, "qty": 6, "stock_qty": 6, "batch_no": "OLD"},
			{"item_code": "IT", "warehouse": "WH", "cr_detail": "CR1", "conversion_factor": 1, "qty": 6, "stock_qty": 6, "batch_no": "OLD"},
		]
		doc = make_doc(rows, {"CR1": 12})
		self._patch(available=[("B1", 3)])
		before = [(i.batch_no, flt(i.stock_qty)) for i in doc.get("items")]
		doc.set_fifo_batch_numbers(force=True)
		after = [(i.batch_no, flt(i.stock_qty)) for i in doc.get("items")]
		self.assertEqual(before, after)
		self.assertEqual(len(doc.get("items")), 2)

	def test_disabled_setting_without_force_is_noop(self):
		# Company auto batch disabled (company=None) and no manual trigger:
		# the whole allocation is skipped and rows stay untouched.
		rows = [
			{"item_code": "IT", "warehouse": "WH", "cr_detail": "CR1", "conversion_factor": 1, "qty": 12, "stock_qty": 12},
		]
		doc = make_doc(rows, {"CR1": 12})
		self._patch(available=[("B1", 5), ("B2", 20)])
		doc.set_fifo_batch_numbers(force=False)
		items = doc.get("items")
		self.assertEqual(len(items), 1)
		self.assertIsNone(items[0].get("batch_no"))
