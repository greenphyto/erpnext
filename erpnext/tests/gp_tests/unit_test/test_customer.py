import os
import frappe
import unittest
from frappe.utils import cstr

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()


def tearDownModule():
	frappe.destroy()


class TestCustomerCodeAutoGeneration(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.series_abbr = cstr(frappe.get_value("Company", self.company, "series_abbr"))

	def test_customer_code_generated_on_insert(self):
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit Customer Code Gen",
			"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group"),
			"territory": frappe.db.get_single_value("Selling Settings", "territory"),
			"company": self.company,
		})
		customer.insert(ignore_permissions=True)
		self.assertTrue(customer.customer_code)
		self.assertTrue(customer.customer_code.startswith(self.series_abbr + "C"))
		customer.delete(ignore_permissions=True)

	def test_cash_sales_customer_code(self):
		expected_code = self.series_abbr + "C00008"
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit Cash Sales Customer",
			"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group"),
			"territory": frappe.db.get_single_value("Selling Settings", "territory"),
			"company": self.company,
			"is_cash_sales": 1,
		})
		customer.insert(ignore_permissions=True)
		self.assertEqual(customer.customer_code, expected_code)
		customer.delete(ignore_permissions=True)

	def test_duplicate_customer_code_throws(self):
		customer1 = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit Dup Code 1",
			"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group"),
			"territory": frappe.db.get_single_value("Selling Settings", "territory"),
			"company": self.company,
		})
		customer1.insert(ignore_permissions=True)

		customer2 = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit Dup Code 2",
			"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group"),
			"territory": frappe.db.get_single_value("Selling Settings", "territory"),
			"company": self.company,
			"customer_code": customer1.customer_code,
		})
		self.assertRaises(frappe.ValidationError, customer2.insert, ignore_permissions=True)
		customer1.delete(ignore_permissions=True)


class TestCustomerSKUValidation(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group")
		self.territory = frappe.db.get_single_value("Selling Settings", "territory")
		self.items = frappe.db.get_all("Item", filters={"disabled": 0}, limit=2, pluck="name")

	def test_validate_sku_no_duplicate_item(self):
		if len(self.items) < 1:
			self.skipTest("No items available")

		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit SKU Dup Item",
			"customer_group": self.customer_group,
			"territory": self.territory,
			"company": self.company,
			"customer_sku": [
				{"item_code": self.items[0], "sku": "SKU001", "origin_name": "Test"},
				{"item_code": self.items[0], "sku": "SKU002", "origin_name": "Test2"},
			]
		})
		self.assertRaises(frappe.ValidationError, customer.insert, ignore_permissions=True)

	def test_validate_sku_no_duplicate_sku_number(self):
		if len(self.items) < 2:
			self.skipTest("Not enough items")

		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit SKU Dup Number",
			"customer_group": self.customer_group,
			"territory": self.territory,
			"company": self.company,
			"customer_sku": [
				{"item_code": self.items[0], "sku": "SAMESKU", "origin_name": "Test"},
				{"item_code": self.items[1], "sku": "SAMESKU", "origin_name": "Test2"},
			]
		})
		self.assertRaises(frappe.ValidationError, customer.insert, ignore_permissions=True)

	def test_sku_name_defaults_to_origin_name(self):
		if len(self.items) < 1:
			self.skipTest("No items available")

		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit SKU Default Name",
			"customer_group": self.customer_group,
			"territory": self.territory,
			"company": self.company,
			"customer_sku": [
				{"item_code": self.items[0], "sku": "SKUDEFAULT01", "origin_name": "Origin Test"},
			]
		})
		customer.insert(ignore_permissions=True)
		sku_row = customer.customer_sku[0]
		self.assertTrue(sku_row.sku_name)
		self.assertEqual(sku_row.sku_name, sku_row.origin_name)
		customer.delete(ignore_permissions=True)


class TestCustomerPackagingValidation(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group")
		self.territory = frappe.db.get_single_value("Selling Settings", "territory")
		self.items = frappe.db.get_all("Item", filters={"disabled": 0, "item_group": "Products"}, limit=1, pluck="name")

	def test_duplicate_item_package_throws(self):
		if len(self.items) < 1:
			self.skipTest("No product items available")

		uom = frappe.db.get_value("UOM", {"is_packaging": 1}, "name")
		if not uom:
			uom = "Kg"

		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit Packaging Dup",
			"customer_group": self.customer_group,
			"territory": self.territory,
			"company": self.company,
			"customer_packaging": [
				{"item_code": self.items[0], "item_name": "Test", "package": uom},
				{"item_code": self.items[0], "item_name": "Test", "package": uom},
			]
		})
		self.assertRaises(frappe.ValidationError, customer.insert, ignore_permissions=True)


class TestCustomerInternalValidation(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group")
		self.territory = frappe.db.get_single_value("Selling Settings", "territory")

	def test_clears_represents_company_when_not_internal(self):
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit Internal Clear",
			"customer_group": self.customer_group,
			"territory": self.territory,
			"company": self.company,
			"is_internal_customer": 0,
			"represents_company": self.company,
		})
		customer.insert(ignore_permissions=True)
		self.assertEqual(customer.represents_company, "")
		customer.delete(ignore_permissions=True)


class TestCustomerDefaultAddress(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group")
		self.territory = frappe.db.get_single_value("Selling Settings", "territory")

	def test_set_default_address_if_linked(self):
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "_Test Unit Address Auto",
			"customer_group": self.customer_group,
			"territory": self.territory,
			"company": self.company,
		})
		customer.insert(ignore_permissions=True)

		address = frappe.get_doc({
			"doctype": "Address",
			"address_title": "_Test Unit Address",
			"address_line1": "123 Test Street",
			"city": "Test City",
			"country": "Indonesia",
			"links": [{"link_doctype": "Customer", "link_name": customer.name}]
		})
		address.insert(ignore_permissions=True)

		customer.reload()
		customer.customer_primary_address = ""
		customer.primary_address = ""
		customer.save(ignore_permissions=True)
		customer.reload()
		self.assertEqual(customer.customer_primary_address, address.name)

		customer.reload()
		customer.customer_primary_address = ""
		customer.primary_address = ""
		customer.db_set("customer_primary_address", "")
		customer.db_set("primary_address", "")
		frappe.db.delete("Dynamic Link", {"link_doctype": "Customer", "link_name": customer.name, "parenttype": "Address"})
		frappe.delete_doc("Address", address.name, ignore_permissions=True, force=True)
		customer.delete(ignore_permissions=True)


if __name__ == "__main__":
	unittest.main()
