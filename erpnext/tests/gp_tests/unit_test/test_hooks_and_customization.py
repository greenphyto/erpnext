import os
import frappe
import unittest
from frappe.utils import flt, cint, nowdate

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestValidateCompanySelected(unittest.TestCase):
	def test_non_company_doctype_passes(self):
		from erpnext.controllers.erp import validate_company_selected
		doc = frappe.new_doc("ToDo")
		try:
			validate_company_selected(doc)
		except Exception:
			self.fail("Should not throw for doctype without company field")


class TestChangeNamingSeriesHooks(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.abbr = frappe.get_value("Company", self.company, "series_abbr")

	def test_purchase_order_gets_prefix(self):
		if not self.abbr:
			self.skipTest("No series_abbr")
		from erpnext.controllers.erp import change_naming_series
		doc = frappe.new_doc("Purchase Order")
		doc.company = self.company
		doc.naming_series = "PO-.YYYY.-.####"
		change_naming_series(doc)
		self.assertTrue(doc.naming_series.startswith(self.abbr))

	def test_material_request_gets_prefix(self):
		if not self.abbr:
			self.skipTest("No series_abbr")
		from erpnext.controllers.erp import change_naming_series
		doc = frappe.new_doc("Material Request")
		doc.company = self.company
		doc.naming_series = "MR-.YYYY.-.####"
		change_naming_series(doc)
		self.assertTrue(doc.naming_series.startswith(self.abbr))


if __name__ == "__main__":
	unittest.main()
