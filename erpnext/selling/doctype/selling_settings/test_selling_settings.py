# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe


class TestSellingSettings(unittest.TestCase):
	def test_defaults_populated(self):
		default = frappe.db.get_single_value("Selling Settings", "maintain_same_rate_action")
		self.assertEqual("Auto Change", default)
