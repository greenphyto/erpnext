import frappe
import unittest
from frappe.utils import flt, getdate, nowdate

import os
SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestConsignmentRequestSetStatus(unittest.TestCase):
	def test_waiting_for_transfer(self):
		cr = frappe.new_doc("Consignment Request")
		cr.per_transfer = 0
		cr.per_sold = 0
		cr.per_delivered = 0
		cr.per_billed = 0
		cr.per_return = 0
		cr.set_status()
		self.assertEqual(cr.status, "Waiting for Tranfer")

	def test_partially_transferred(self):
		cr = frappe.new_doc("Consignment Request")
		cr.per_transfer = 50
		cr.per_sold = 0
		cr.per_delivered = 0
		cr.per_billed = 0
		cr.per_return = 0
		cr.set_status()
		self.assertEqual(cr.status, "Partially Transfered")

	def test_transferred_to_customer(self):
		cr = frappe.new_doc("Consignment Request")
		cr.per_transfer = 100
		cr.per_sold = 0
		cr.per_delivered = 0
		cr.per_billed = 0
		cr.per_return = 0
		cr.set_status()
		self.assertEqual(cr.status, "Transfered to Customer")

	def test_returned_and_to_bill(self):
		cr = frappe.new_doc("Consignment Request")
		cr.per_transfer = 100
		cr.per_sold = 50
		cr.per_return = 20
		cr.per_delivered = 0
		cr.per_billed = 0
		cr.set_status()
		self.assertEqual(cr.status, "Returned and To Bill")

	def test_to_bill(self):
		cr = frappe.new_doc("Consignment Request")
		cr.per_transfer = 100
		cr.per_sold = 50
		cr.per_delivered = 50
		cr.per_billed = 0
		cr.per_return = 0
		cr.set_status()
		self.assertEqual(cr.status, "To Bill")

	def test_completed(self):
		cr = frappe.new_doc("Consignment Request")
		cr.per_transfer = 100
		cr.per_sold = 100
		cr.per_delivered = 100
		cr.per_billed = 100
		cr.per_return = 0
		cr.set_status()
		self.assertEqual(cr.status, "Completed")


class TestConsignmentRequestSyncQty(unittest.TestCase):
	def test_sync_qty_calculates_percentages(self):
		cr = frappe.new_doc("Consignment Request")
		cr.total_qty = 100
		cr.append("items", {
			"item_code": "TEST",
			"qty": 50,
			"transfer_qty": 30,
			"returned_qty": 5,
			"sold_qty": 25,
			"billed_qty": 10,
			"delivered_qty": 10,
		})
		cr.append("items", {
			"item_code": "TEST2",
			"qty": 50,
			"transfer_qty": 20,
			"returned_qty": 0,
			"sold_qty": 20,
			"billed_qty": 5,
			"delivered_qty": 5,
		})

		cr.total_transfer_qty = 0
		cr.total_return_qty = 0
		cr.total_sold_qty = 0
		cr.total_billed_qty = 0
		cr.total_delivered_qty = 0

		for d in cr.get("items"):
			cr.total_transfer_qty += flt(d.transfer_qty)
			cr.total_sold_qty += flt(d.sold_qty)
			cr.total_return_qty += flt(d.returned_qty)
			cr.total_billed_qty += flt(d.billed_qty)
			cr.total_delivered_qty += flt(d.delivered_qty)

		cr.per_transfer = flt(cr.total_transfer_qty / flt(cr.total_qty) * 100 if cr.total_qty else 0, 2)
		cr.per_return = flt(cr.total_return_qty / flt(cr.total_transfer_qty) * 100 if cr.total_transfer_qty else 0, 2)
		cr.per_sold = flt(cr.total_sold_qty / flt(cr.total_transfer_qty) * 100 if cr.total_transfer_qty else 0, 2)
		cr.per_billed = flt(cr.total_billed_qty / flt(cr.total_sold_qty) * 100 if cr.total_sold_qty else 0, 2)
		cr.per_delivered = flt(cr.total_delivered_qty / flt(cr.total_sold_qty) * 100 if cr.total_sold_qty else 0, 2)

		self.assertEqual(cr.total_transfer_qty, 50)
		self.assertEqual(cr.total_return_qty, 5)
		self.assertEqual(cr.total_sold_qty, 45)
		self.assertEqual(cr.total_billed_qty, 15)
		self.assertEqual(cr.total_delivered_qty, 15)
		self.assertEqual(cr.per_transfer, 50.0)
		self.assertAlmostEqual(cr.per_return, 10.0, places=1)
		self.assertAlmostEqual(cr.per_sold, 90.0, places=1)


class TestConsignmentOrderGLEntries(unittest.TestCase):
	def test_get_gl_entries_returns_empty(self):
		if not frappe.db.exists("DocType", "Consignment Order"):
			self.skipTest("Consignment Order doctype not found")
		co = frappe.new_doc("Consignment Order")
		result = co.get_gl_entries()
		self.assertEqual(result, [])


class TestConsignmentOrderNamingSeries(unittest.TestCase):
	def test_before_insert_sets_naming_series(self):
		if not frappe.db.exists("DocType", "Consignment Order"):
			self.skipTest("Consignment Order doctype not found")
		co = frappe.new_doc("Consignment Order")
		co.naming_series = ""
		co.before_insert()
		self.assertEqual(co.naming_series, "CON-.YYYY.-.#####")


if __name__ == "__main__":
	unittest.main()
