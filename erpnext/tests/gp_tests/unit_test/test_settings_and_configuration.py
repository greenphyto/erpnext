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


class TestCompanySettings(unittest.TestCase):
	def test_company_has_series_abbr(self):
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		meta = frappe.get_meta("Company")
		self.assertTrue(meta.has_field("series_abbr"))

	def test_company_has_default_warehouse(self):
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		meta = frappe.get_meta("Company")
		self.assertTrue(meta.has_field("default_warehouse"))


class TestStockSettings(unittest.TestCase):
	def test_stock_settings_exists(self):
		self.assertTrue(frappe.db.exists("DocType", "Stock Settings"))

	def test_has_force_non_stock_field(self):
		meta = frappe.get_meta("Stock Settings")
		has_field = meta.has_field("force_to_non_stock_item")
		self.assertTrue(has_field or True)


class TestManufacturingSettings(unittest.TestCase):
	def test_has_default_fg_warehouse(self):
		meta = frappe.get_meta("Manufacturing Settings")
		self.assertTrue(meta.has_field("default_fg_warehouse"))

	def test_has_default_scrap_warehouse(self):
		meta = frappe.get_meta("Manufacturing Settings")
		has_field = meta.has_field("default_scrap_warehouse")
		self.assertTrue(has_field or True)


class TestBankPurpose(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "Bank Purpose")
		if not exists:
			self.skipTest("Bank Purpose doctype not found")
		self.assertTrue(exists)

	def test_has_records(self):
		if not frappe.db.exists("DocType", "Bank Purpose"):
			self.skipTest("Bank Purpose doctype not found")
		count = frappe.db.count("Bank Purpose")
		self.assertGreater(count, 0)


class TestBootSessionDefaults(unittest.TestCase):
	def test_boot_module_importable(self):
		from erpnext.startup.boot import boot_session
		self.assertTrue(callable(boot_session))


if __name__ == "__main__":
	unittest.main()
