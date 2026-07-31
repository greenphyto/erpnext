import frappe
import unittest
from frappe.utils import flt, getdate, nowdate, get_first_day

SITE_NAME = "test5"
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestGetExchangeRate(unittest.TestCase):
	def test_same_currency_returns_one(self):
		from erpnext.setup.utils import get_exchange_rate
		result = get_exchange_rate("SGD", "SGD", nowdate())
		self.assertEqual(result, 1)

	def test_empty_currency_returns_none(self):
		from erpnext.setup.utils import get_exchange_rate
		result = get_exchange_rate("", "SGD", nowdate())
		self.assertIsNone(result)

	def test_none_currency_returns_none(self):
		from erpnext.setup.utils import get_exchange_rate
		result = get_exchange_rate(None, "SGD", nowdate())
		self.assertIsNone(result)

	def test_returns_numeric_value(self):
		from erpnext.setup.utils import get_exchange_rate
		result = get_exchange_rate("USD", "SGD", nowdate())
		if result:
			self.assertIsInstance(result, (int, float))
			self.assertGreater(result, 0)


class TestSaveCurrencyExchange(unittest.TestCase):
	def test_save_with_rate(self):
		from erpnext.setup.utils import save_currency_exchange

		save_fetched = frappe.db.get_single_value("Accounts Settings", "save_fetched_currency_exchange_rates")
		if not save_fetched:
			self.skipTest("save_fetched_currency_exchange_rates not enabled")

		test_date = "2020-01-01"
		existing = frappe.db.exists("Currency Exchange", {
			"date": test_date,
			"from_currency": "USD",
			"to_currency": "SGD",
		})
		if existing:
			self.skipTest("Currency Exchange record already exists for test date")

		save_currency_exchange("USD", "SGD", date=test_date, rate=1.35)
		exists = frappe.db.exists("Currency Exchange", {
			"date": test_date,
			"from_currency": "USD",
			"to_currency": "SGD",
		})
		self.assertTrue(exists)
		frappe.delete_doc("Currency Exchange", exists, force=True)
		frappe.db.commit()


class TestFirstDayOfMonthLogic(unittest.TestCase):
	def test_first_day_flag_exists_in_settings(self):
		settings = frappe.get_cached_doc("Currency Exchange Settings")
		self.assertTrue(hasattr(settings, "use_rate_as_first_day_of_month_rate"))


if __name__ == "__main__":
	unittest.main()
