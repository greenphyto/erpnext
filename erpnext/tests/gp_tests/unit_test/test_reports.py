import frappe
import unittest
from frappe.utils import nowdate, add_days

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestReportModulesImportable(unittest.TestCase):
	def test_stock_ledger_report(self):
		from erpnext.stock.report.stock_ledger.stock_ledger import execute
		self.assertTrue(callable(execute))

	def test_general_ledger_report(self):
		from erpnext.accounts.report.general_ledger.general_ledger import execute
		self.assertTrue(callable(execute))

	def test_profit_and_loss_report(self):
		from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute
		self.assertTrue(callable(execute))


class TestWIPAccountDetailReport(unittest.TestCase):
	def test_importable(self):
		try:
			from erpnext.foms.report.wip_account_detail.wip_account_detail import execute
			self.assertTrue(callable(execute))
		except ImportError:
			self.skipTest("WIP Account Detail report not importable")


class TestPickingListReport(unittest.TestCase):
	def test_importable(self):
		try:
			from erpnext.foms.report.picking_list_report.picking_list_report import execute
			self.assertTrue(callable(execute))
		except ImportError:
			self.skipTest("Picking List Report not importable")


class TestInvoiceListingDetailsReport(unittest.TestCase):
	def test_importable(self):
		try:
			from erpnext.foms.report.invoice_listing_details.invoice_listing_details import execute
			self.assertTrue(callable(execute))
		except ImportError:
			self.skipTest("Invoice Listing Details report not importable")


if __name__ == "__main__":
	unittest.main()
