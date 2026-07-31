import os
import frappe
import unittest
from frappe.utils import flt, cint

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestJournalEntryValidateCostCenter(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_pl_account_gets_cost_center_from_mapping(self):
		account = frappe.db.get_value("Account", {
			"company": self.company,
			"report_type": "Profit and Loss",
			"cost_center": ["!=", ""],
			"is_group": 0
		}, "name")
		if not account:
			self.skipTest("No P&L account with cost center")

		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.append("accounts", {"account": account, "debit_in_account_currency": 100, "cost_center": ""})
		je.validate_cost_center()
		self.assertTrue(je.accounts[0].cost_center)

	def test_bs_account_skipped(self):
		account = frappe.db.get_value("Account", {
			"company": self.company,
			"report_type": "Balance Sheet",
			"is_group": 0
		}, "name")
		if not account:
			self.skipTest("No BS account found")

		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.append("accounts", {"account": account, "debit_in_account_currency": 100, "cost_center": ""})
		je.validate_cost_center()
		self.assertFalse(je.accounts[0].cost_center)


class TestJournalEntryValidateGSTInput(unittest.TestCase):
	def test_gst_input_without_party_throws(self):
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "GST Input Tax"
		je.party_name = ""
		je.invoice_no = ""
		self.assertRaises(Exception, je.validate_gst_input)

	def test_gst_input_with_party_passes(self):
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "GST Input Tax"
		je.party_name = "Some Supplier"
		je.invoice_no = "INV-001"
		try:
			je.validate_gst_input()
		except Exception:
			self.fail("validate_gst_input raised unexpectedly")

	def test_non_gst_voucher_type_passes(self):
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.party_name = ""
		je.invoice_no = ""
		try:
			je.validate_gst_input()
		except Exception:
			self.fail("validate_gst_input raised for non-GST type")


class TestJournalEntryValidateReferencePayment(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")
		self.mandatory = frappe.db.get_single_value("Accounts Settings", "mandatory_reference_on_journal_entry")

	def test_payable_debit_without_reference_throws(self):
		if not self.mandatory:
			self.skipTest("mandatory_reference_on_journal_entry not enabled")

		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.append("accounts", {
			"account": "test",
			"account_type": "Payable",
			"is_advance": "No",
			"debit": 100,
			"credit": 0,
			"reference_name": "",
		})
		self.assertRaises(Exception, je.validate_reference_payment)

	def test_payable_credit_passes_without_reference(self):
		if not self.mandatory:
			self.skipTest("mandatory_reference_on_journal_entry not enabled")

		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.append("accounts", {
			"account": "test",
			"account_type": "Payable",
			"is_advance": "No",
			"debit": 0,
			"credit": 100,
			"reference_name": "",
		})
		try:
			je.validate_reference_payment()
		except Exception:
			self.fail("Should not throw for payable credit without reference")


if __name__ == "__main__":
	unittest.main()
