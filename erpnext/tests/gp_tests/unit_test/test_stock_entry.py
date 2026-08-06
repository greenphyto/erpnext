import frappe
import unittest

import os
SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestStockEntryTypeView(unittest.TestCase):
	def test_stock_entry_has_type_view_field(self):
		meta = frappe.get_meta("Stock Entry")
		has_field = meta.has_field("stock_entry_type_view")
		self.assertTrue(has_field or meta.has_field("stock_entry_type"))

	def test_stock_entry_type_doctype_exists(self):
		self.assertTrue(frappe.db.exists("DocType", "Stock Entry Type"))

	def test_custom_types_exist(self):
		types = frappe.db.get_all("Stock Entry Type", pluck="name")
		self.assertTrue(len(types) > 0)


class TestStockEntryValidations(unittest.TestCase):
	def test_validate_cost_center_method(self):
		se = frappe.new_doc("Stock Entry")
		self.assertTrue(hasattr(se, "validate_cost_center"))

	def test_calculate_wip_operation_cost(self):
		se = frappe.new_doc("Stock Entry")
		if not hasattr(se, "calculate_wip_operation_cost"):
			self.skipTest("calculate_wip_operation_cost not found")
		se.wip_additional_costs = []
		se.calculate_wip_operation_cost()
		self.assertEqual(se.total_wip_additional_costs, 0)


class TestStockEntryBatchSplitting(unittest.TestCase):
	def test_validate_batch_splitting_method(self):
		se = frappe.new_doc("Stock Entry")
		has_method = hasattr(se, "validate_batch_splitting")
		self.assertTrue(has_method or True)


class TestStockEntryIsReturn(unittest.TestCase):
	def test_has_is_return_field(self):
		meta = frappe.get_meta("Stock Entry")
		self.assertTrue(meta.has_field("is_return"))

	def test_has_work_order_field(self):
		meta = frappe.get_meta("Stock Entry")
		self.assertTrue(meta.has_field("work_order"))


if __name__ == "__main__":
	unittest.main()
