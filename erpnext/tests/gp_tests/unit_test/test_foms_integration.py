import frappe
import unittest

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestFomsIntegrationUOMMapping(unittest.TestCase):
	def setUp(self):
		try:
			from erpnext.controllers.foms import get_uom
			self.get_uom = get_uom
		except ImportError:
			self.skipTest("foms controller not importable")

	def test_known_uom_mapping(self):
		result = self.get_uom("kg")
		self.assertEqual(result, "Kg")

	def test_unknown_uom_throws(self):
		self.assertRaises(Exception, self.get_uom, "UNKNOWN_UOM_XYZ_99")


class TestFomsIsAllowedCompany(unittest.TestCase):
	def test_function_exists(self):
		try:
			from erpnext.controllers.foms import is_allowed_foms_company
			company = frappe.db.get_single_value("Global Defaults", "default_company")
			result = is_allowed_foms_company(company)
			self.assertIsInstance(result, bool)
		except (ImportError, AttributeError):
			self.skipTest("is_allowed_foms_company not available")


class TestFomsConvertData(unittest.TestCase):
	def setUp(self):
		try:
			from erpnext.controllers.foms import FomsAPI
			self.api = FomsAPI
		except ImportError:
			self.skipTest("FomsAPI not importable")

	def test_replaces_none_with_empty(self):
		import json
		api = self.api.__new__(self.api)
		data = {"key": None, "nested": {"val": None, "ok": "test"}}
		result = json.loads(api.convert_data(data))
		self.assertEqual(result["key"], "")
		self.assertEqual(result["nested"]["val"], "")
		self.assertEqual(result["nested"]["ok"], "test")

	def test_list_with_none(self):
		import json
		api = self.api.__new__(self.api)
		data = [None, "hello", {"x": None}]
		result = json.loads(api.convert_data(data))
		self.assertEqual(result[0], "")
		self.assertEqual(result[1], "hello")
		self.assertEqual(result[2]["x"], "")


if __name__ == "__main__":
	unittest.main()
