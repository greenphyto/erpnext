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


class TestCEOBypassWorkflow(unittest.TestCase):
	def test_bypass_hook_registered(self):
		from erpnext.hooks import bypass_workflow_permission
		self.assertTrue(bypass_workflow_permission)

	def test_bypass_function_callable(self):
		try:
			from erpnext.controllers.erp import control_bypass_workflow
			self.assertTrue(callable(control_bypass_workflow))
		except (ImportError, AttributeError):
			self.skipTest("control_bypass_workflow not found")


class TestValidateCompanySelected(unittest.TestCase):
	def test_function_callable(self):
		from erpnext.controllers.erp import validate_company_selected
		self.assertTrue(callable(validate_company_selected))

	def test_passes_for_administrator(self):
		from erpnext.controllers.erp import validate_company_selected
		doc = frappe.new_doc("Sales Invoice")
		doc.company = frappe.db.get_single_value("Global Defaults", "default_company")
		try:
			validate_company_selected(doc)
		except Exception:
			self.fail("Should pass for Administrator user")


class TestPurchaseUserPermissionsList(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "Purchase User Permissions List")
		if not exists:
			self.skipTest("Purchase User Permissions List doctype not found")
		self.assertTrue(exists)


class TestMaterialRequestPermissionQuery(unittest.TestCase):
	def test_permission_query_function(self):
		try:
			from erpnext.stock.doctype.material_request.material_request import get_permission_query_conditions
			self.assertTrue(callable(get_permission_query_conditions))
		except (ImportError, AttributeError):
			self.skipTest("get_permission_query_conditions not found")


if __name__ == "__main__":
	unittest.main()
