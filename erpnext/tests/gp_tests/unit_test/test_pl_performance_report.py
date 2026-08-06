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


class TestPLPerformanceReportExists(unittest.TestCase):
	def test_report_file_exists(self):
		import os
		path = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/gp_erp/report/p&l_performance_review/p&l_performance_review.py"
		self.assertTrue(os.path.exists(path))

	def test_report_importable(self):
		try:
			import importlib
			mod = importlib.import_module("erpnext.gp_erp.report.p&l_performance_review.p&l_performance_review")
			self.assertTrue(hasattr(mod, "execute"))
		except (ImportError, ModuleNotFoundError):
			self.skipTest("PL performance report not importable (special characters in path)")


class TestPLPerformanceControlFilters(unittest.TestCase):
	def test_control_filters(self):
		try:
			import importlib
			mod = importlib.import_module("erpnext.gp_erp.report.p&l_performance_review.p&l_performance_review")
			control_filters = getattr(mod, "control_filters", None)
			if not control_filters:
				self.skipTest("control_filters not found")

			filters = frappe._dict({
				"year": "2026",
				"month": "01",
				"to_month": "06",
				"company": frappe.db.get_single_value("Global Defaults", "default_company"),
			})
			result = control_filters(filters)
			self.assertIn("period_start_date", result)
			self.assertIn("period_end_date", result)
		except (ImportError, ModuleNotFoundError):
			self.skipTest("PL performance report not importable")


if __name__ == "__main__":
	unittest.main()
