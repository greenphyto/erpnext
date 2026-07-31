import frappe
import unittest
from frappe.utils import flt, nowdate

from erpnext.buying.doctype.request.request import (
	_resolve_item,
	_resolve_customer,
	_get_existing_request,
)

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestForecastSettingsResolveItem(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("Forecast Settings"):
			self.skipTest("Forecast Settings not found")
		self.settings = frappe.get_doc("Forecast Settings")
		if not self.settings.enable:
			self.skipTest("Forecast Settings not enabled")

	def test_existing_mapping(self):
		items = [r for r in self.settings.items if r.ref_doctype == "Item" and r.custom_name]
		if not items:
			self.skipTest("No item mappings")
		row = items[0]
		self.assertEqual(_resolve_item(row.custom_name, self.settings), row.ref_name)

	def test_nonexistent_returns_none(self):
		self.assertIsNone(_resolve_item("ZZZZZ_NONEXIST", self.settings))


class TestForecastSettingsResolveCustomer(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("Forecast Settings"):
			self.skipTest("Forecast Settings not found")
		self.settings = frappe.get_doc("Forecast Settings")
		if not self.settings.enable:
			self.skipTest("Forecast Settings not enabled")

	def test_existing_mapping(self):
		customers = [r for r in self.settings.customers if r.ref_doctype == "Customer" and r.custom_name]
		if not customers:
			self.skipTest("No customer mappings")
		row = customers[0]
		self.assertEqual(_resolve_customer(row.custom_name, self.settings), row.ref_name)


class TestGetExistingRequest(unittest.TestCase):
	def test_nonexistent_returns_none(self):
		result = _get_existing_request("FAKE_CUSTOMER_XYZ", "2099-12-31")
		self.assertIsNone(result)


if __name__ == "__main__":
	unittest.main()
