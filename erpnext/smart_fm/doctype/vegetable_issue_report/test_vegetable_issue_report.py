# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestVegetableIssueReport(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("User", "test_crop_reporter@example.com"):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": "test_crop_reporter@example.com",
					"first_name": "Test Crop Reporter",
					"new_password": "test123",
					"role_profile_name": None,
				}
			)
			user.append("roles", {"role": "System Manager"})
			user.insert(ignore_permissions=True)

	def _make_report(self, **kwargs):
		doc = frappe.get_doc(
			{
				"doctype": "Vegetable Issue Report",
				"reported_by": "test_crop_reporter@example.com",
				"date_reported": frappe.utils.today(),
				"product_name": "Test Item - Vegetable Issue",
				"lot_id": "LOT-TEST-001",
				"item_affected": "Seeds",
				"issues_symptoms": "Test symptom description",
				"status": "Draft",
				**kwargs,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_vegetable_issue_report(self):
		doc = self._make_report()
		self.assertTrue(doc.name.startswith("VIR-"))
		self.assertEqual(doc.status, "Draft")

	def test_affected_quantity_validation_cages(self):
		doc = self._make_report(
			num_cages_affected=10,
			total_cages_in_lot=5,
		)
		self.assertRaises(frappe.exceptions.ValidationError, doc.save)

	def test_affected_quantity_validation_trays(self):
		doc = self._make_report(
			num_trays_affected=20,
			total_trays_in_lot=15,
		)
		self.assertRaises(frappe.exceptions.ValidationError, doc.save)

	def test_affected_tray_child_table(self):
		doc = self._make_report()
		doc.append(
			"affected_tray_details",
			{"cage_id": "CAGE-001", "tray_id": "TRAY-001", "location_sz": "SZ-A1"},
		)
		doc.save()
		self.assertEqual(len(doc.affected_tray_details), 1)
		self.assertEqual(doc.affected_tray_details[0].cage_id, "CAGE-001")
