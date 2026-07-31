import frappe
import unittest

import os
SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestBankNumberValidation(unittest.TestCase):
	def test_hsbc_short_number_throws(self):
		try:
			from erpnext.accounts.doctype.bank_number.bank_number import check_branch_code_mandatory
		except ImportError:
			self.skipTest("bank_number module not available")

		result = check_branch_code_mandatory("HSBC", "12345")
		self.assertTrue(result)

	def test_hsbc_long_number_passes(self):
		try:
			from erpnext.accounts.doctype.bank_number.bank_number import check_branch_code_mandatory
		except ImportError:
			self.skipTest("bank_number module not available")

		result = check_branch_code_mandatory("HSBC", "1234567890")
		self.assertFalse(result)

	def test_non_restricted_bank_passes(self):
		try:
			from erpnext.accounts.doctype.bank_number.bank_number import check_branch_code_mandatory
		except ImportError:
			self.skipTest("bank_number module not available")

		result = check_branch_code_mandatory("DBS", "12345")
		self.assertFalse(result)


class TestUOBPaymentXMLStructure(unittest.TestCase):
	def test_get_country_code(self):
		try:
			from erpnext.controllers.uob import get_country_code
		except ImportError:
			self.skipTest("uob controller not available")

		result = get_country_code("Singapore")
		self.assertEqual(result, "SG")

	def test_get_country_code_indonesia(self):
		try:
			from erpnext.controllers.uob import get_country_code
		except ImportError:
			self.skipTest("uob controller not available")

		result = get_country_code("Indonesia")
		self.assertEqual(result, "ID")


if __name__ == "__main__":
	unittest.main()
