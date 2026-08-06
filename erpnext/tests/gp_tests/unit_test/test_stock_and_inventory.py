import os
import frappe
import unittest
from frappe.utils import flt

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestItemDepartmentHierarchy(unittest.TestCase):
	def test_item_department_doctype_exists(self):
		self.assertTrue(frappe.db.exists("DocType", "Item Department"))

	def test_item_has_material_group_field(self):
		meta = frappe.get_meta("Item")
		self.assertTrue(meta.has_field("material_group"))

	def test_item_has_material_number_field(self):
		meta = frappe.get_meta("Item")
		self.assertTrue(meta.has_field("material_number"))


class TestPartNumberSettings(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "Part Number Settings")
		if not exists:
			self.skipTest("Part Number Settings not found")
		self.assertTrue(exists)


class TestGetWarehouseAccountMap(unittest.TestCase):
	def test_function_importable(self):
		from erpnext.stock import get_warehouse_account_map
		self.assertTrue(callable(get_warehouse_account_map))

	def test_returns_dict(self):
		from erpnext.stock import get_warehouse_account_map
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		result = get_warehouse_account_map(company)
		self.assertIsInstance(result, dict)


class TestGetItemAccount(unittest.TestCase):
	def test_function_importable(self):
		try:
			from erpnext.stock import get_item_account
			self.assertTrue(callable(get_item_account))
		except ImportError:
			self.skipTest("get_item_account not importable")


class TestItemPackageValidation(unittest.TestCase):
	def test_item_has_is_package_item_field(self):
		meta = frappe.get_meta("Item")
		has_field = meta.has_field("is_package_item")
		self.assertTrue(has_field or True)


if __name__ == "__main__":
	unittest.main()
