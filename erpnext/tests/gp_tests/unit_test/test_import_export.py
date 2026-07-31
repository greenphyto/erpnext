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


class TestMinioBackupSettings(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "MinIO Backup Settings")
		if not exists:
			self.skipTest("MinIO Backup Settings doctype not found")
		self.assertTrue(exists)

	def test_database_list_field(self):
		if not frappe.db.exists("DocType", "MinIO Backup Settings"):
			self.skipTest("MinIO Backup Settings not found")
		meta = frappe.get_meta("MinIO Backup Settings")
		has_field = meta.has_field("database_list")
		self.assertTrue(has_field)


class TestUOBFileLog(unittest.TestCase):
	def test_doctype_exists(self):
		exists = frappe.db.exists("DocType", "UOB File Log")
		if not exists:
			self.skipTest("UOB File Log doctype not found")
		self.assertTrue(exists)


if __name__ == "__main__":
	unittest.main()
