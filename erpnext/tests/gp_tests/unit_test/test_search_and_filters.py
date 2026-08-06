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


class TestItemQuery(unittest.TestCase):
	def test_function_exists(self):
		from erpnext.controllers.queries import item_query
		self.assertTrue(callable(item_query))

	def test_basic_search(self):
		from erpnext.controllers.queries import item_query
		result = item_query("Item", "PR", "name", 0, 20, {})
		self.assertIsInstance(result, (list, tuple))

	def test_search_with_department_filter(self):
		from erpnext.controllers.queries import item_query
		dept = frappe.db.get_value("Department", {}, "name")
		if not dept:
			self.skipTest("No department found")
		result = item_query("Item", "", "name", 0, 20, {"department": dept})
		self.assertIsInstance(result, (list, tuple))


class TestUOMQuery(unittest.TestCase):
	def test_function_exists(self):
		try:
			from erpnext.controllers.queries import uom
			self.assertTrue(callable(uom))
		except (ImportError, AttributeError):
			self.skipTest("uom query not found")

	def test_basic_search(self):
		try:
			from erpnext.controllers.queries import uom
		except (ImportError, AttributeError):
			self.skipTest("uom query not found")
		result = uom("UOM", "Kg", "name", 0, 20, {})
		self.assertIsInstance(result, (list, tuple))


class TestGetCompanyEnable(unittest.TestCase):
	def test_function_exists(self):
		from erpnext.controllers.queries import get_company_enable
		self.assertTrue(callable(get_company_enable))

	def test_returns_list(self):
		from erpnext.controllers.queries import get_company_enable
		result = get_company_enable()
		self.assertIsInstance(result, (list, tuple))


if __name__ == "__main__":
	unittest.main()
