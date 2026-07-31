import os
import frappe
import unittest
from frappe.utils import flt

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestInvoiceValidateQtyNotZero(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_zero_qty_item_throws(self):
		si = frappe.new_doc("Sales Invoice")
		si.company = self.company
		si.is_return = 0
		si.is_debit_note = 0
		si.append("items", {
			"item_code": "TEST",
			"qty": 0,
			"rate": 100,
		})
		self.assertRaises(Exception, si.validate_qty_is_not_zero)

	def test_positive_qty_passes(self):
		si = frappe.new_doc("Sales Invoice")
		si.company = self.company
		si.is_return = 0
		si.is_debit_note = 0
		si.append("items", {
			"item_code": "TEST",
			"qty": 5,
			"rate": 100,
		})
		try:
			si.validate_qty_is_not_zero()
		except Exception:
			self.fail("validate_qty_is_not_zero raised unexpectedly")

	def test_purchase_receipt_skips_validation(self):
		pr = frappe.new_doc("Purchase Receipt")
		pr.company = self.company
		pr.append("items", {
			"item_code": "TEST",
			"qty": 0,
			"rate": 100,
		})
		try:
			pr.validate_qty_is_not_zero()
		except Exception:
			self.fail("Purchase Receipt should skip zero qty validation")


if __name__ == "__main__":
	unittest.main()
