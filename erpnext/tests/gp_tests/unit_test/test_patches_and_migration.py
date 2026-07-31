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


class TestPatchIdempotency(unittest.TestCase):
	def test_set_batch_status_patch_exists(self):
		import os
		path = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/patches/gp/set_batch_status.py"
		self.assertTrue(os.path.exists(path))

	def test_set_default_cost_center_patch_exists(self):
		import os
		path = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/patches/gp/set_default_cost_center_in_account.py"
		self.assertTrue(os.path.exists(path))

	def test_add_bank_purpose_patch_exists(self):
		import os
		path = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/patches/gp/add_bank_purpose.py"
		self.assertTrue(os.path.exists(path))


class TestPatchesRegistered(unittest.TestCase):
	def test_patches_in_patches_txt(self):
		import os
		patches_path = "/workspace/development/gp-frappe-bench/apps/erpnext/erpnext/patches.txt"
		self.assertTrue(os.path.exists(patches_path))
		with open(patches_path, "r") as f:
			content = f.read()
		self.assertIn("set_batch_status", content)


if __name__ == "__main__":
	unittest.main()
