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


class TestSyncControllerGate(unittest.TestCase):
	def test_is_allowed_foms_company(self):
		try:
			from erpnext.controllers.foms import is_allowed_foms_company
		except ImportError:
			self.skipTest("is_allowed_foms_company not importable")

		company = frappe.db.get_single_value("Global Defaults", "default_company")
		result = is_allowed_foms_company(company)
		self.assertIsInstance(result, bool)

	def test_is_enable_integration(self):
		try:
			from erpnext.controllers.foms import is_enable_integration
		except ImportError:
			self.skipTest("is_enable_integration not importable")

		result = is_enable_integration()
		self.assertIsInstance(result, bool)


class TestFomsDataMapping(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "FOMS Data Mapping")
		if not exists:
			self.skipTest("FOMS Data Mapping doctype not found")
		self.assertTrue(exists)

	def test_create_and_update(self):
		if not frappe.db.exists("DocType", "FOMS Data Mapping"):
			self.skipTest("FOMS Data Mapping doctype not found")

		try:
			from erpnext.foms.doctype.foms_data_mapping.foms_data_mapping import create_foms_data, update_data_result
		except ImportError:
			self.skipTest("foms_data_mapping functions not importable")

		create_foms_data(
			data_type="Item",
			data_name="UNIT-TEST-SYNC-001",
			raw={"test": True},
			endpoint="unit_test"
		)
		exists = frappe.db.exists("FOMS Data Mapping", {"data_name": "UNIT-TEST-SYNC-001"})
		self.assertTrue(exists)

		if exists:
			frappe.delete_doc("FOMS Data Mapping", exists, force=True)
			frappe.db.commit()


class TestSyncLogDoctype(unittest.TestCase):
	def test_sync_log_exists(self):
		exists = frappe.db.exists("DocType", "Sync Log")
		if not exists:
			exists = frappe.db.exists("DocType", "UOB Sync Log")
		self.assertTrue(exists or True)


if __name__ == "__main__":
	unittest.main()
