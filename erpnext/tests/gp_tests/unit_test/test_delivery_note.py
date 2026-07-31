import frappe
import unittest
from frappe.utils import cint, flt, nowdate, getdate

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestDeliveryNoteValidateNonStock(unittest.TestCase):
	def test_non_stock_clears_warehouse(self):
		dn = frappe.new_doc("Delivery Note")
		dn.non_stock_item = 1
		dn.append("items", {
			"item_code": "Test",
			"qty": 1,
			"warehouse": "Some Warehouse",
		})
		dn.validate_non_stock()
		for d in dn.get("items"):
			self.assertEqual(d.warehouse, "")

	def test_stock_item_keeps_warehouse(self):
		dn = frappe.new_doc("Delivery Note")
		dn.non_stock_item = 0
		dn.append("items", {
			"item_code": "Test",
			"qty": 1,
			"warehouse": "Some Warehouse",
		})
		dn.validate_non_stock()
		self.assertEqual(dn.items[0].warehouse, "Some Warehouse")


class TestDeliveryNoteValidatePledge(unittest.TestCase):
	def test_donor_customer_sets_is_pledge(self):
		dn = frappe.new_doc("Delivery Note")
		dn.customer = "Donor"
		dn.donor_name = "Test Donor"
		dn.validate_pledge()
		self.assertEqual(dn.is_pledge, 1)

	def test_non_donor_does_not_set_pledge(self):
		dn = frappe.new_doc("Delivery Note")
		dn.customer = "Some Customer"
		dn.is_pledge = 0
		dn.validate_pledge()
		self.assertEqual(dn.is_pledge, 0)

	def test_donor_sets_contact_display_from_donor_name(self):
		dn = frappe.new_doc("Delivery Note")
		dn.customer = "Donor"
		dn.donor_name = "John Doe"
		dn.contact_display = ""
		dn.validate_pledge()
		self.assertEqual(dn.contact_display, "John Doe")


class TestDeliveryNoteValidateDonation(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_donation_without_org_name_throws(self):
		dn = frappe.new_doc("Delivery Note")
		dn.company = self.company
		dn.is_donation = 1
		dn.organization_name = ""
		self.assertRaises(Exception, dn.validate_donation)

	def test_pledge_without_donor_name_throws(self):
		dn = frappe.new_doc("Delivery Note")
		dn.company = self.company
		dn.is_pledge = 1
		dn.donor_name = ""
		dn.is_donation = 0
		self.assertRaises(Exception, dn.validate_donation)

	def test_donation_sets_expense_account(self):
		donation_account = frappe.get_value("Company", self.company, "donation_account")
		if not donation_account:
			self.skipTest("No donation_account set in company")

		dn = frappe.new_doc("Delivery Note")
		dn.company = self.company
		dn.is_donation = 1
		dn.organization_name = "Test Org"
		dn.is_pledge = 0
		dn.is_giveaway = 0
		dn.is_replacement = 0
		dn.is_production = 0
		dn.is_marketing = 0
		dn.append("items", {"item_code": "Test", "qty": 1, "expense_account": ""})
		dn.validate_donation()
		self.assertEqual(dn.items[0].expense_account, donation_account)

	def test_giveaway_sets_expense_account(self):
		giveaway_account = frappe.get_value("Company", self.company, "giveaway_account")
		if not giveaway_account:
			self.skipTest("No giveaway_account set in company")

		dn = frappe.new_doc("Delivery Note")
		dn.company = self.company
		dn.is_donation = 0
		dn.is_giveaway = 1
		dn.is_pledge = 0
		dn.is_replacement = 0
		dn.is_production = 0
		dn.is_marketing = 0
		dn.append("items", {"item_code": "Test", "qty": 1, "expense_account": ""})
		dn.validate_donation()
		self.assertEqual(dn.items[0].expense_account, giveaway_account)

	def test_replacement_sets_expense_account(self):
		replacement_account = frappe.get_value("Company", self.company, "sales_replacement_account")
		if not replacement_account:
			self.skipTest("No sales_replacement_account set in company")

		dn = frappe.new_doc("Delivery Note")
		dn.company = self.company
		dn.is_donation = 0
		dn.is_giveaway = 0
		dn.is_replacement = 1
		dn.is_pledge = 0
		dn.is_production = 0
		dn.is_marketing = 0
		dn.append("items", {"item_code": "Test", "qty": 1, "expense_account": ""})
		dn.validate_donation()
		self.assertEqual(dn.items[0].expense_account, replacement_account)


class TestDeliveryNoteValidateReplacement(unittest.TestCase):
	def test_replacement_without_reason_throws(self):
		dn = frappe.new_doc("Delivery Note")
		dn.is_replacement = 1
		dn.replacement_reason = ""
		self.assertRaises(frappe.ValidationError, dn.validate_replacement)

	def test_replacement_with_reason_passes(self):
		dn = frappe.new_doc("Delivery Note")
		dn.is_replacement = 1
		dn.replacement_reason = "Damaged product"
		try:
			dn.validate_replacement()
		except frappe.ValidationError:
			self.fail("validate_replacement raised ValidationError unexpectedly")

	def test_non_replacement_passes(self):
		dn = frappe.new_doc("Delivery Note")
		dn.is_replacement = 0
		dn.replacement_reason = ""
		try:
			dn.validate_replacement()
		except frappe.ValidationError:
			self.fail("validate_replacement raised ValidationError for non-replacement DN")


class TestDeliveryNoteValidatePackedQty(unittest.TestCase):
	def test_packed_qty_mismatch_throws(self):
		dn = frappe.new_doc("Delivery Note")
		dn.append("items", {"item_code": "Test", "qty": 10, "packed_qty": 5})
		self.assertRaises(frappe.ValidationError, dn.validate_packed_qty)

	def test_packed_qty_match_passes(self):
		dn = frappe.new_doc("Delivery Note")
		dn.append("items", {"item_code": "Test", "qty": 10, "packed_qty": 10})
		try:
			dn.validate_packed_qty()
		except frappe.ValidationError:
			self.fail("validate_packed_qty raised ValidationError unexpectedly")

	def test_no_packed_qty_passes(self):
		dn = frappe.new_doc("Delivery Note")
		dn.append("items", {"item_code": "Test", "qty": 10, "packed_qty": 0})
		try:
			dn.validate_packed_qty()
		except frappe.ValidationError:
			self.fail("validate_packed_qty raised for zero packed_qty")


if __name__ == "__main__":
	unittest.main()
