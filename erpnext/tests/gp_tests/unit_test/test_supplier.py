import frappe
import unittest
from frappe.utils import cstr

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestSupplierCodeGeneration(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.series_abbr = cstr(frappe.get_value("Company", self.company, "series_abbr"))

	def test_new_supplier_gets_code(self):
		supplier_group = frappe.db.get_single_value("Buying Settings", "supplier_group") or frappe.db.get_value("Supplier Group", {}, "name")
		if not supplier_group:
			self.skipTest("No supplier group found")
		supplier = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": "_Test Unit Supplier Code Gen",
			"supplier_group": supplier_group,
			"company": self.company,
		})
		supplier.insert(ignore_permissions=True)
		self.assertTrue(supplier.supplier_code)
		supplier.delete(ignore_permissions=True)

	def test_duplicate_code_gets_new_code(self):
		supplier_group = frappe.db.get_single_value("Buying Settings", "supplier_group") or frappe.db.get_value("Supplier Group", {}, "name")
		if not supplier_group:
			self.skipTest("No supplier group found")
		supplier1 = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": "_Test Unit Sup Dup1",
			"supplier_group": supplier_group,
			"company": self.company,
		})
		supplier1.insert(ignore_permissions=True)

		supplier2 = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": "_Test Unit Sup Dup2",
			"supplier_group": supplier_group,
			"company": self.company,
		})
		supplier2.insert(ignore_permissions=True)
		self.assertNotEqual(supplier1.supplier_code, supplier2.supplier_code)
		supplier2.delete(ignore_permissions=True)
		supplier1.delete(ignore_permissions=True)


class TestSupplierInternalValidation(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_clears_represents_company_when_not_internal(self):
		supplier_group = frappe.db.get_single_value("Buying Settings", "supplier_group") or frappe.db.get_value("Supplier Group", {}, "name")
		if not supplier_group:
			self.skipTest("No supplier group found")
		supplier = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": "_Test Unit Sup Internal",
			"supplier_group": supplier_group,
			"company": self.company,
			"is_internal_supplier": 0,
			"represents_company": self.company,
		})
		supplier.insert(ignore_permissions=True)
		self.assertEqual(supplier.represents_company, "")
		supplier.delete(ignore_permissions=True)


if __name__ == "__main__":
	unittest.main()
