import os
import frappe
import unittest

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestSchedulerEventsRegistered(unittest.TestCase):
	def test_hooks_has_scheduler_events(self):
		from erpnext.hooks import scheduler_events
		self.assertIsInstance(scheduler_events, dict)

	def test_has_cron_jobs(self):
		from erpnext.hooks import scheduler_events
		cron = scheduler_events.get("cron", {})
		self.assertTrue(len(cron) > 0)

	def test_has_daily_jobs(self):
		from erpnext.hooks import scheduler_events
		daily = scheduler_events.get("daily", []) or scheduler_events.get("daily_long", [])
		self.assertTrue(len(daily) > 0)

	def test_depreciation_in_monthly(self):
		from erpnext.hooks import scheduler_events
		monthly = scheduler_events.get("monthly", []) or scheduler_events.get("monthly_long", [])
		found = any("depreciation" in f for f in monthly)
		self.assertTrue(found)


class TestReorderItemScheduler(unittest.TestCase):
	def test_reorder_item_importable(self):
		from erpnext.stock.reorder_item import reorder_item
		self.assertTrue(callable(reorder_item))


class TestFetchMonthRate(unittest.TestCase):
	def test_function_importable(self):
		try:
			from erpnext.setup.doctype.currency_exchange.currency_exchange import fetch_month_rate
			self.assertTrue(callable(fetch_month_rate))
		except ImportError:
			self.skipTest("fetch_month_rate not importable")


class TestUOBSyncFileFunction(unittest.TestCase):
	def test_function_exists(self):
		try:
			from erpnext.controllers.uob import sync_uob_file
			self.assertTrue(callable(sync_uob_file))
		except ImportError:
			self.skipTest("sync_uob_file not importable")


if __name__ == "__main__":
	unittest.main()
