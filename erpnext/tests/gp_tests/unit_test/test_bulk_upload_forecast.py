import os
import frappe
import unittest
from frappe.utils import flt, getdate, nowdate

from erpnext.buying.doctype.request.request import (
	_resolve_item,
	_resolve_customer,
	_resolve_packaging,
	_get_item_price,
	_get_existing_request,
	_add_item_to_request,
	parse_forecast_upload,
)

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestResolveItem(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("Forecast Settings"):
			self.skipTest("Forecast Settings not found")
		self.settings = frappe.get_doc("Forecast Settings")
		if not self.settings.enable:
			self.skipTest("Forecast Settings not enabled")

	def test_resolve_existing_item(self):
		items_with_ref = [r for r in self.settings.items if r.ref_doctype == "Item" and r.custom_name]
		if not items_with_ref:
			self.skipTest("No item mappings in Forecast Settings")

		row = items_with_ref[0]
		result = _resolve_item(row.custom_name, self.settings)
		self.assertEqual(result, row.ref_name)

	def test_resolve_nonexistent_item_returns_none(self):
		result = _resolve_item("NONEXISTENT_VEGGIE_XYZ", self.settings)
		self.assertIsNone(result)


class TestResolveCustomer(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("Forecast Settings"):
			self.skipTest("Forecast Settings not found")
		self.settings = frappe.get_doc("Forecast Settings")
		if not self.settings.enable:
			self.skipTest("Forecast Settings not enabled")

	def test_resolve_existing_customer(self):
		customers = [r for r in self.settings.customers if r.ref_doctype == "Customer" and r.custom_name]
		if not customers:
			self.skipTest("No customer mappings in Forecast Settings")

		row = customers[0]
		result = _resolve_customer(row.custom_name, self.settings)
		self.assertEqual(result, row.ref_name)

	def test_resolve_nonexistent_customer_returns_none(self):
		result = _resolve_customer("NONEXISTENT_CUSTOMER_XYZ", self.settings)
		self.assertIsNone(result)


class TestResolvePackaging(unittest.TestCase):
	def test_nonexistent_item_returns_none(self):
		result = _resolve_packaging("ITEM_DOES_NOT_EXIST_XYZ", 0.2)
		self.assertIsNone(result)

	def test_existing_item_with_packaging(self):
		pla = frappe.db.get_value(
			"Packaging List Available",
			{"weight": [">", 0]},
			["parent", "weight", "package_item"],
			as_dict=True
		)
		if not pla:
			self.skipTest("No Packaging List Available with weight found")

		result = _resolve_packaging(pla.parent, flt(pla.weight))
		self.assertIsNotNone(result)
		self.assertEqual(result.get("package_item"), pla.package_item)


class TestGetItemPrice(unittest.TestCase):
	def test_returns_number(self):
		item = frappe.db.get_value("Item", {"disabled": 0}, "name")
		if not item:
			self.skipTest("No active item found")
		result = _get_item_price(item)
		self.assertIsInstance(result, (int, float))

	def test_nonexistent_item_returns_zero(self):
		result = _get_item_price("NONEXISTENT_ITEM_XYZ_99999")
		self.assertEqual(result, 0)


class TestGetExistingRequest(unittest.TestCase):
	def test_no_existing_returns_none(self):
		result = _get_existing_request("NONEXISTENT_CUSTOMER_XYZ", "2099-12-31")
		self.assertIsNone(result)


class TestParseForecastUpload(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("Forecast Settings"):
			self.skipTest("Forecast Settings not found")
		settings = frappe.get_doc("Forecast Settings")
		if not settings.enable:
			self.skipTest("Forecast Settings not enabled")

	def test_empty_csv_throws(self):
		self.assertRaises(Exception, parse_forecast_upload, "")

	def test_missing_columns_throws(self):
		csv = "Name,Value\nA,1"
		self.assertRaises(Exception, parse_forecast_upload, csv)

	def test_valid_csv_returns_structure(self):
		csv = "Delivery Date,Customer,Vegetable,Predicted Packages,UOM (g),Predicted Kg,Unit Price (SGD)\n"
		csv += "2099-01-01,FakeCustomer,FakeVeg,10,200,2.0,5.0\n"
		result = parse_forecast_upload(csv)
		self.assertIn("groups", result)
		self.assertIn("warnings", result)
		self.assertIn("summary", result)
		self.assertTrue(len(result["warnings"]) > 0)


if __name__ == "__main__":
	unittest.main()
