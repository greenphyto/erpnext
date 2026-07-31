import frappe
import unittest
from frappe.utils import flt, getdate, nowdate, add_days

from erpnext.stock.doctype.batch.batch import (
	get_batch_status,
	get_item_shelf_life_in_days,
	get_available_batch_portion,
)

import os
SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestGetBatchStatus(unittest.TestCase):
	def test_empty_when_qty_zero(self):
		self.assertEqual(get_batch_status(0, None), "Empty")

	def test_empty_when_qty_negative(self):
		self.assertEqual(get_batch_status(-5, None), "Empty")

	def test_expired_when_past_date(self):
		past_date = add_days(nowdate(), -10)
		self.assertEqual(get_batch_status(10, past_date), "Expired")

	def test_active_when_has_qty_no_expiry(self):
		self.assertEqual(get_batch_status(10, None), "Active")

	def test_active_when_has_qty_future_expiry(self):
		future_date = add_days(nowdate(), 30)
		self.assertEqual(get_batch_status(10, future_date), "Active")

	def test_empty_takes_priority_over_expired(self):
		past_date = add_days(nowdate(), -10)
		self.assertEqual(get_batch_status(0, past_date), "Empty")


class TestGetItemShelfLifeInDays(unittest.TestCase):
	def test_returns_tuple(self):
		item = frappe.db.get_value("Item", {"has_expiry_date": 1, "disabled": 0}, "name")
		if not item:
			self.skipTest("No item with expiry tracking found")
		result = get_item_shelf_life_in_days(item)
		self.assertIsInstance(result, tuple)
		self.assertEqual(len(result), 2)
		self.assertEqual(result[0], 1)

	def test_item_without_expiry(self):
		item = frappe.db.get_value("Item", {"has_expiry_date": 0, "disabled": 0}, "name")
		if not item:
			self.skipTest("No item without expiry found")
		result = get_item_shelf_life_in_days(item)
		self.assertEqual(result[0], 0)

	def test_company_specific_shelf_life(self):
		row = frappe.db.get_value(
			"Shell Life Companies",
			{},
			["parent", "company", "shelf_life_in_days"],
			as_dict=True
		)
		if not row:
			self.skipTest("No Shell Life Companies data found")

		ref_doctype = "Purchase Receipt"
		ref_name = frappe.db.get_value(ref_doctype, {"company": row.company, "docstatus": 1}, "name")
		if not ref_name:
			self.skipTest(f"No submitted {ref_doctype} for company {row.company}")

		_, shelf_life = get_item_shelf_life_in_days(row.parent, ref_doctype, ref_name)
		self.assertEqual(shelf_life, row.shelf_life_in_days)


class TestGetAvailableBatchPortion(unittest.TestCase):
	def test_returns_list(self):
		item = frappe.db.get_value("Item", {"has_batch_no": 1, "disabled": 0}, "name")
		if not item:
			self.skipTest("No batch-tracked item found")
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		result = get_available_batch_portion(item, 1, company=company)
		self.assertIsInstance(result, list)

	def test_fifo_strategy(self):
		item = frappe.db.get_value("Item", {"has_batch_no": 1, "disabled": 0}, "name")
		if not item:
			self.skipTest("No batch-tracked item found")
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		result = get_available_batch_portion(item, 1, company=company, strategy="FIFO")
		self.assertIsInstance(result, list)

	def test_zero_qty_returns_empty(self):
		item = frappe.db.get_value("Item", {"has_batch_no": 1, "disabled": 0}, "name")
		if not item:
			self.skipTest("No batch-tracked item found")
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		result = get_available_batch_portion(item, 0, company=company)
		self.assertEqual(result, [])


class TestPickBatches(unittest.TestCase):
	def test_pick_batches_returns_list(self):
		from erpnext.stock.doctype.batch.batch import pick_batches

		item = frappe.db.get_value("Item", {"has_batch_no": 1, "disabled": 0}, "name")
		if not item:
			self.skipTest("No batch-tracked item found")

		company = frappe.db.get_single_value("Global Defaults", "default_company")
		warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
		if not warehouse:
			self.skipTest("No warehouse found")

		result = pick_batches(item, warehouse, 1)
		self.assertIsInstance(result, list)


if __name__ == "__main__":
	unittest.main()
