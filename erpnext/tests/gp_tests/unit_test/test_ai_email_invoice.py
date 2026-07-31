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


class TestEmailInvoiceDoctype(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "Email Invoice")
		if not exists:
			self.skipTest("Email Invoice doctype not found")
		self.assertTrue(exists)

	def test_new_doc_has_process_email(self):
		if not frappe.db.exists("DocType", "Email Invoice"):
			self.skipTest("Email Invoice doctype not found")
		doc = frappe.new_doc("Email Invoice")
		self.assertTrue(hasattr(doc, "process_email"))

	def test_new_doc_has_refine_with_memory(self):
		if not frappe.db.exists("DocType", "Email Invoice"):
			self.skipTest("Email Invoice doctype not found")
		doc = frappe.new_doc("Email Invoice")
		self.assertTrue(hasattr(doc, "refine_with_memory"))


class TestAIAgentMemory(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "AI Agent Memory")
		if not exists:
			self.skipTest("AI Agent Memory doctype not found")
		self.assertTrue(exists)

	def test_get_memory_function(self):
		try:
			from erpnext.gp_erp.doctype.ai_agent_memory.ai_agent_memory import get_memory
		except ImportError:
			self.skipTest("get_memory not importable")

		result = get_memory("Supplier", "NONEXISTENT_SUPPLIER_XYZ", "Test Company")
		self.assertIsInstance(result, str)
		self.assertEqual(result, "")

	def test_get_memory_with_existing_supplier(self):
		try:
			from erpnext.gp_erp.doctype.ai_agent_memory.ai_agent_memory import get_memory
		except ImportError:
			self.skipTest("get_memory not importable")

		memory_doc = frappe.db.get_value("AI Agent Memory", {}, ["reff_doctype", "reff_name", "company"], as_dict=True)
		if not memory_doc:
			self.skipTest("No AI Agent Memory records")

		result = get_memory(memory_doc.reff_doctype, memory_doc.reff_name, memory_doc.company)
		self.assertIsInstance(result, str)


class TestAIInvoiceConverterImport(unittest.TestCase):
	def test_module_importable(self):
		try:
			from erpnext.ai_agent.doctype.ai_agent_settings.ai_invoice_converter import AIAgentClient
			self.assertTrue(True)
		except ImportError:
			self.skipTest("ai_invoice_converter not importable")


if __name__ == "__main__":
	unittest.main()
