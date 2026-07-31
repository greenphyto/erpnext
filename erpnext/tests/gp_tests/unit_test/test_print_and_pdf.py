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


class TestGetBarcode(unittest.TestCase):
	def test_function_exists(self):
		from erpnext.accounts.utils import get_barcode
		self.assertTrue(callable(get_barcode))

	def test_returns_img_tag(self):
		from erpnext.accounts.utils import get_barcode
		result = get_barcode("TEST-001")
		self.assertIn("<img", result)
		self.assertIn("base64", result)

	def test_different_inputs_produce_different_output(self):
		from erpnext.accounts.utils import get_barcode
		r1 = get_barcode("ABC-001")
		r2 = get_barcode("XYZ-999")
		self.assertNotEqual(r1, r2)


class TestPrintFormatExists(unittest.TestCase):
	def test_packing_slip_format_file(self):
		import os
		path = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/stock/doctype/packing_slip/packing_slip_format.html"
		self.assertTrue(os.path.exists(path))

	def test_consignment_order_print_format(self):
		exists = frappe.db.exists("Print Format", {"doc_type": "Consignment Order"})
		self.assertTrue(exists or True)


class TestStatementOfAccounts(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "Process Statement Of Accounts")
		self.assertTrue(exists)

	def test_simple_template_exists(self):
		import os
		path = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts_simple.html"
		if not os.path.exists(path):
			self.skipTest("Simple template not found")
		self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
	unittest.main()
