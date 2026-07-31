import os
import frappe
import unittest
from frappe.utils import cstr, cint, nowdate, getdate, flt

import erpnext
from erpnext.accounts.utils import get_cost_center_from_account

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()


def tearDownModule():
	frappe.destroy()


class TestGetDefaultCostCenter(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_returns_none_without_company(self):
		result = erpnext.get_default_cost_center(company="", account="")
		self.assertIsNone(result)

	def test_returns_cost_center_from_account_field(self):
		account = frappe.db.get_value("Account", {
			"company": self.company,
			"cost_center": ["!=", ""],
			"is_group": 0
		}, "name")
		if not account:
			self.skipTest("No account with cost_center field set")

		expected_cc = frappe.get_value("Account", account, "cost_center")
		result = erpnext.get_default_cost_center(company=self.company, account=account)
		self.assertEqual(result, expected_cc)

	def test_returns_cost_center_from_mapping(self):
		mappings = frappe.db.get_all("Cost Center Mapping", {
			"company": self.company
		}, ["account", "cost_center"])
		if not mappings:
			self.skipTest("No Cost Center Mapping found")

		mapping = None
		for m in mappings:
			account_cc = frappe.get_value("Account", m.account, "cost_center")
			if not account_cc:
				mapping = m
				break

		if not mapping:
			self.skipTest("All mapped accounts have cost_center set directly")

		result = erpnext.get_default_cost_center(company=self.company, account=mapping.account)
		self.assertEqual(result, mapping.cost_center)


class TestGetCostCenterFromAccount(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_empty_account_returns_unlock(self):
		result = get_cost_center_from_account("", self.company)
		self.assertEqual(result, {"value": "", "lock": 0})

	def test_account_with_mapping_returns_locked(self):
		account = frappe.db.get_value("Account", {
			"company": self.company,
			"cost_center": ["!=", ""],
			"is_group": 0
		}, "name")
		if not account:
			self.skipTest("No account with cost_center mapping")

		result = get_cost_center_from_account(account, self.company)
		self.assertEqual(result["lock"], 1)
		self.assertTrue(result["value"])

	def test_balance_sheet_account_locked_empty(self):
		account = frappe.db.get_value("Account", {
			"company": self.company,
			"account_number": ["like", "1%"],
			"is_group": 0,
			"cost_center": ["in", ["", None]]
		}, "name")
		if not account:
			account = frappe.db.get_value("Account", {
				"company": self.company,
				"account_number": ["like", "2%"],
				"is_group": 0,
				"cost_center": ["in", ["", None]]
			}, "name")
		if not account:
			self.skipTest("No Balance Sheet account without cost center found")

		result = get_cost_center_from_account(account, self.company)
		self.assertEqual(result["lock"], 1)
		self.assertEqual(result["value"], "")

	def test_pl_account_without_mapping_unlocked(self):
		account = frappe.db.get_value("Account", {
			"company": self.company,
			"report_type": "Profit and Loss",
			"is_group": 0,
			"cost_center": ["in", ["", None]],
			"account_number": ["not like", "1%"],
		}, "name")
		if not account:
			self.skipTest("No P&L account without cost center mapping")

		has_mapping = frappe.db.get_value("Cost Center Mapping", {
			"company": self.company,
			"account": account
		})
		if has_mapping:
			self.skipTest("Account has a Cost Center Mapping")

		result = get_cost_center_from_account(account, self.company)
		self.assertEqual(result["lock"], 0)


class TestGLEntrySetDefaultCostCenter(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_pl_account_auto_fills_cost_center(self):
		account = frappe.db.get_value("Account", {
			"company": self.company,
			"report_type": "Profit and Loss",
			"cost_center": ["!=", ""],
			"is_group": 0
		}, "name")
		if not account:
			self.skipTest("No P&L account with cost_center set")

		expected_cc = erpnext.get_default_cost_center(company=self.company, account=account)

		gl = frappe.new_doc("GL Entry")
		gl.account = account
		gl.company = self.company
		gl.cost_center = ""
		gl.set_default_cost_center_value()
		self.assertEqual(gl.cost_center, expected_cc)

	def test_bs_account_does_not_auto_fill(self):
		account = frappe.db.get_value("Account", {
			"company": self.company,
			"report_type": "Balance Sheet",
			"is_group": 0
		}, "name")
		if not account:
			self.skipTest("No Balance Sheet account found")

		gl = frappe.new_doc("GL Entry")
		gl.account = account
		gl.company = self.company
		gl.cost_center = ""
		gl.set_default_cost_center_value()
		self.assertFalse(gl.cost_center)


class TestGLEntryPLMustHaveCostCenter(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_pl_without_cost_center_throws(self):
		account = frappe.db.get_value("Account", {
			"company": self.company,
			"report_type": "Profit and Loss",
			"cost_center": ["in", ["", None]],
			"is_group": 0,
		}, "name")
		if not account:
			self.skipTest("No P&L account without cost center")

		has_mapping = frappe.db.get_value("Cost Center Mapping", {
			"company": self.company,
			"account": account
		})
		if has_mapping:
			self.skipTest("Account has mapping, will auto-fill")

		gl = frappe.new_doc("GL Entry")
		gl.account = account
		gl.company = self.company
		gl.cost_center = ""
		gl.voucher_type = "Journal Entry"
		gl.voucher_no = "TEST-JV-0001"
		gl.posting_date = nowdate()
		gl.set_default_cost_center_value()

		if gl.cost_center:
			self.skipTest("Cost center got auto-filled")

		self.assertRaises(frappe.ValidationError, gl.pl_must_have_cost_center)

	def test_pl_with_cost_center_does_not_throw(self):
		cost_center = frappe.db.get_value("Cost Center", {
			"company": self.company,
			"is_group": 0
		}, "name")
		if not cost_center:
			self.skipTest("No cost center found")

		account = frappe.db.get_value("Account", {
			"company": self.company,
			"report_type": "Profit and Loss",
			"is_group": 0,
		}, "name")
		if not account:
			self.skipTest("No P&L account found")

		gl = frappe.new_doc("GL Entry")
		gl.account = account
		gl.company = self.company
		gl.cost_center = cost_center
		gl.voucher_type = "Journal Entry"
		gl.voucher_no = "TEST-JV-0002"
		gl.posting_date = nowdate()

		try:
			gl.pl_must_have_cost_center()
		except frappe.ValidationError:
			self.fail("pl_must_have_cost_center raised ValidationError unexpectedly")


class TestAllowCostCenterMissing(unittest.TestCase):
	def setUp(self):
		self.company = frappe.db.get_single_value("Global Defaults", "default_company")

	def test_old_posting_date_allows_missing(self):
		from erpnext.accounts.doctype.gl_entry.gl_entry import allow_cost_center_missing

		gl = frappe.new_doc("GL Entry")
		gl.posting_date = "2020-01-01"
		result = allow_cost_center_missing(gl)
		self.assertTrue(result)

	def test_current_date_does_not_allow_missing(self):
		from erpnext.accounts.doctype.gl_entry.gl_entry import allow_cost_center_missing

		gl = frappe.new_doc("GL Entry")
		gl.posting_date = nowdate()
		result = allow_cost_center_missing(gl)
		self.assertFalse(result)


if __name__ == "__main__":
	unittest.main()
