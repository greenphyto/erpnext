import frappe
import unittest
from frappe.utils import flt, cint

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestPaymentApprovalValidatePayment(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Payment Approval"):
			self.skipTest("Payment Approval doctype not found")

	def test_transfer_tt_sets_urgp(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_type = "Transfer"
		pa.payment_method = "TT"
		pa.validate_payment()
		self.assertEqual(pa.method["method"], "URGP")
		self.assertEqual(pa.method["type"], "TRF")

	def test_transfer_paynow_sets_urns_paynow(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_type = "Transfer"
		pa.payment_method = "PayNow"
		pa.validate_payment()
		self.assertEqual(pa.method["method"], "URNS")
		self.assertEqual(pa.method["property"], "PAYNOW")

	def test_transfer_fast_sets_urns(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_type = "Transfer"
		pa.payment_method = "FAST"
		pa.validate_payment()
		self.assertEqual(pa.method["method"], "URNS")

	def test_transfer_ibg_sets_nurg(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_type = "Transfer"
		pa.payment_method = "IBG"
		pa.validate_payment()
		self.assertEqual(pa.method["method"], "NURG")

	def test_transfer_ibg_express_sets_book(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_type = "Transfer"
		pa.payment_method = "IBG Express"
		pa.validate_payment()
		self.assertEqual(pa.method["method"], "BOOK")

	def test_transfer_invalid_method_throws(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_type = "Transfer"
		pa.payment_method = "INVALID"
		self.assertRaises(Exception, pa.validate_payment)

	def test_cheque_type_sets_chk(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_type = "Cheque"
		pa.payment_property = "CHQ"
		pa.validate_payment()
		self.assertEqual(pa.method["type"], "CHK")
		self.assertEqual(pa.method["property"], "CCHQ")


class TestPaymentApprovalCalculateAmount(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Payment Approval"):
			self.skipTest("Payment Approval doctype not found")

	def test_totals_invoices(self):
		pa = frappe.new_doc("Payment Approval")
		pa.append("invoices", {"basic_amount": 100})
		pa.append("invoices", {"basic_amount": 250.50})
		pa.calculate_amount()
		self.assertAlmostEqual(pa.total_amount, 350.50, places=2)

	def test_empty_invoices(self):
		pa = frappe.new_doc("Payment Approval")
		pa.calculate_amount()
		self.assertEqual(pa.total_amount, 0)


class TestPaymentApprovalSetBatchNumber(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Payment Approval"):
			self.skipTest("Payment Approval doctype not found")

	def test_extracts_batch_from_name(self):
		pa = frappe.new_doc("Payment Approval")
		pa.name = "PAY-2600450"
		pa.batch_number = ""
		pa.set_batch_number()
		self.assertEqual(pa.batch_number, 450)

	def test_no_pay_in_name_skips(self):
		pa = frappe.new_doc("Payment Approval")
		pa.name = "OTHER-001"
		pa.batch_number = ""
		pa.set_batch_number()
		self.assertFalse(pa.batch_number)


class TestPaymentApprovalValidatePaynow(unittest.TestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Payment Approval"):
			self.skipTest("Payment Approval doctype not found")

	def test_paynow_without_proxy_throws(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_method = "PayNow"
		pa.append("invoices", {
			"proxy_number": "",
			"supplier_bank_no": "123456",
			"basic_amount": 100,
		})
		self.assertRaises(Exception, pa.validate_paynow)

	def test_paynow_with_proxy_passes(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_method = "PayNow"
		pa.append("invoices", {
			"proxy_number": "912345678",
			"supplier_bank_no": "123456",
			"basic_amount": 100,
		})
		try:
			pa.validate_paynow()
		except Exception:
			self.fail("validate_paynow raised unexpectedly")

	def test_non_paynow_skips_validation(self):
		pa = frappe.new_doc("Payment Approval")
		pa.payment_method = "TT"
		pa.append("invoices", {
			"proxy_number": "",
			"supplier_bank_no": "123456",
			"basic_amount": 100,
		})
		try:
			pa.validate_paynow()
		except Exception:
			self.fail("validate_paynow raised for non-PayNow")


if __name__ == "__main__":
	unittest.main()
