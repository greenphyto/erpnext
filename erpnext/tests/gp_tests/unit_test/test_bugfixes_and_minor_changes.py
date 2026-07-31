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


class TestBugfixGLEntryAgainstAccount(unittest.TestCase):
	def test_gl_entry_has_against_account_field(self):
		meta = frappe.get_meta("GL Entry")
		self.assertTrue(meta.has_field("against_account"))

	def test_gl_entry_has_against_party_field(self):
		meta = frappe.get_meta("GL Entry")
		self.assertTrue(meta.has_field("against_party"))

	def test_gl_entry_has_against_account_number_field(self):
		meta = frappe.get_meta("GL Entry")
		self.assertTrue(meta.has_field("against_account_number"))


class TestBugfixStockLedgerEntry(unittest.TestCase):
	def test_sle_has_batch_no_field(self):
		meta = frappe.get_meta("Stock Ledger Entry")
		self.assertTrue(meta.has_field("batch_no"))

	def test_sle_has_actual_qty_field(self):
		meta = frappe.get_meta("Stock Ledger Entry")
		self.assertTrue(meta.has_field("actual_qty"))


class TestBugfixWorkOrderStatus(unittest.TestCase):
	def test_work_order_has_produced_qty(self):
		meta = frappe.get_meta("Work Order")
		self.assertTrue(meta.has_field("produced_qty"))

	def test_work_order_has_material_transferred(self):
		meta = frappe.get_meta("Work Order")
		self.assertTrue(meta.has_field("material_transferred_for_manufacturing"))


class TestBugfixPackingSlipModule(unittest.TestCase):
	def test_packing_slip_module_reference(self):
		meta = frappe.get_meta("Packing Slip")
		self.assertTrue(meta.module)


class TestBugfixScrapAccountField(unittest.TestCase):
	def test_stock_entry_has_is_return(self):
		meta = frappe.get_meta("Stock Entry")
		self.assertTrue(meta.has_field("is_return"))


if __name__ == "__main__":
	unittest.main()
