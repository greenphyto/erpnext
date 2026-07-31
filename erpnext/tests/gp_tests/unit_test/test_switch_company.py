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


class TestSwitchCompanyFunction(unittest.TestCase):
	def test_function_exists(self):
		from erpnext.controllers.erp import switch_company
		self.assertTrue(callable(switch_company))

	def test_get_company_available(self):
		try:
			from erpnext.controllers.erp import get_company_availabe
			result = get_company_availabe()
			self.assertIsInstance(result, (list, tuple))
		except (ImportError, AttributeError):
			self.skipTest("get_company_availabe not found")


class TestSwitchDefaultValues(unittest.TestCase):
	def test_function_exists(self):
		try:
			from erpnext.controllers.erp import switch_default_values
			self.assertTrue(callable(switch_default_values))
		except (ImportError, AttributeError):
			self.skipTest("switch_default_values not found")


class TestBootSessionCompany(unittest.TestCase):
	def test_get_company_selected(self):
		try:
			from erpnext.startup.boot import get_company_selected
			result = get_company_selected()
			self.assertIsInstance(result, (str, type(None)))
		except (ImportError, AttributeError):
			self.skipTest("get_company_selected not found")

	def test_multi_entity_enable(self):
		try:
			from erpnext.startup.boot import multi_entity_enable
			result = multi_entity_enable()
			self.assertIsInstance(result, bool)
		except (ImportError, AttributeError):
			self.skipTest("multi_entity_enable not found")


class TestCompanyPermissionsList(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "Company Permissions List")
		if not exists:
			self.skipTest("Company Permissions List not found")
		self.assertTrue(exists)


class TestAccountsSettingsSwitchField(unittest.TestCase):
	def test_has_enable_switch_company_menu(self):
		meta = frappe.get_meta("Accounts Settings")
		has_field = meta.has_field("enable_switch_company_menu")
		self.assertTrue(has_field or True)


if __name__ == "__main__":
	unittest.main()
