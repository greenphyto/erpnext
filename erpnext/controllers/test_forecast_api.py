# Copyright (c) 2026, Green Phygto and contributors
# For license information, please see license.txt

import frappe
import json
import unittest
from erpnext.controllers.erp_api import receive_forecast


class TestForecastAPI(unittest.TestCase):
	def setUp(self):
		# Enable Forecast Settings
		settings = frappe.get_doc("Forecast Settings", "Forecast Settings")
		settings.enable = 1
		settings.save()

	def test_receive_forecast_invalid_payload_string(self):
		"""Test that invalid payload (string) throws error"""
		with self.assertRaises(Exception):
			receive_forecast("invalid")

	def test_receive_forecast_empty_payload(self):
		"""Test that empty payload throws error"""
		with self.assertRaises(Exception):
			receive_forecast([])

	def test_receive_forecast_missing_fields(self):
		"""Test that missing required fields throws error"""
		data = [{"veg_name": "Kai Lan"}]  # Missing packages, uom_in_kg, forecast_date, customer
		try:
			receive_forecast(data)
			self.fail("Should have thrown error for missing fields")
		except Exception as e:
			self.assertIn("missing fields", str(e).lower())

	def test_receive_forecast_unknown_customer(self):
		"""Test that unknown customer is skipped"""
		data = [
			{
				"veg_name": "Kai Lan",
				"packages": 100,
				"uom_in_kg": 0.11,
				"total_kg": 11,
				"forecast_date": "2026-07-20",
				"customer": "UNKNOWN_CUSTOMER"
			}
		]
		result = receive_forecast(data)
		# Should return result with failed items
		self.assertIn("details", result)
		self.assertTrue(len(result["details"]) > 0)
		self.assertEqual(result["details"][0]["status"], "failed")

	def test_receive_forecast_unknown_item(self):
		"""Test that unknown item is skipped"""
		# This test requires Forecast Settings with customer mapping but no item mapping
		settings = frappe.get_doc("Forecast Settings", "Forecast Settings")
		if settings.customers:
			customer_name = settings.customers[0].custom_name
			data = [
				{
					"veg_name": "UNKNOWN_ITEM",
					"packages": 100,
					"uom_in_kg": 0.11,
					"total_kg": 11,
					"forecast_date": "2026-07-20",
					"customer": customer_name
				}
			]
			result = receive_forecast(data)
			self.assertIn("details", result)
			self.assertTrue(len(result["details"]) > 0)
			self.assertEqual(result["details"][0]["status"], "failed")
