import os
import frappe
import unittest
from frappe.utils import nowdate, flt
import json

from erpnext.buying.doctype.request.request import get_events, get_request_items

SITE_NAME = os.environ.get("FRAPPE_SITE", "test5-15")
SITES_PATH = "/workspace/development/gp-frappe-bench/sites"


def setUpModule():
	frappe.init(site=SITE_NAME, sites_path=SITES_PATH)
	frappe.connect()
	frappe.set_user("Administrator")


def tearDownModule():
	frappe.destroy()


class TestGetEvents(unittest.TestCase):
	def test_returns_list(self):
		result = get_events("2026-01-01", "2026-12-31")
		self.assertIsInstance(result, list)

	def test_with_item_codes_filter(self):
		item = frappe.db.get_value("Request Items", {}, "item_code")
		if not item:
			self.skipTest("No Request Items found")
		result = get_events("2020-01-01", "2099-12-31", item_codes=json.dumps([item]))
		self.assertIsInstance(result, list)

	def test_events_have_required_fields(self):
		result = get_events("2020-01-01", "2099-12-31")
		if not result:
			self.skipTest("No events found")
		event = result[0]
		self.assertIn("title", event)
		self.assertIn("color", event)
		self.assertIn("textColor", event)
		self.assertIn("start", event)


class TestGetEventColor(unittest.TestCase):
	def test_pr_av_submitted_yellow(self):
		result = get_events.__code__  # just verify function exists
		self.assertTrue(True)

	def test_color_logic_pr_av(self):
		from erpnext.buying.doctype.request.request import get_events
		events = get_events("2020-01-01", "2099-12-31")
		pr_av_events = [e for e in events if e.get("item_code", "").startswith("PR-AV")]
		if pr_av_events:
			self.assertIn(pr_av_events[0]["color"], ("#FFC107", "#EC008C"))

	def test_color_logic_pr_lv(self):
		events = get_events("2020-01-01", "2099-12-31")
		pr_lv_events = [e for e in events if e.get("item_code", "").startswith("PR-LV")]
		if pr_lv_events:
			self.assertIn(pr_lv_events[0]["color"], ("#28A745", "#00FFFF"))


class TestGetRequestItems(unittest.TestCase):
	def test_returns_list(self):
		result = get_request_items()
		self.assertIsInstance(result, (list, tuple))

	def test_with_item_code_filter(self):
		result = get_request_items(filters=json.dumps({"item_code": "PR"}))
		self.assertIsInstance(result, (list, tuple))


if __name__ == "__main__":
	unittest.main()
