# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cstr
from erpnext.accounts.utils import get_account_number_map


class CostCenterSettings(Document):
	def validate(self):
		for d in self.get("cost_center"):
			d.company = self.company

	def on_update(self):
		"""Sync cost center back to Account doctype"""
		self._sync_cost_center_to_accounts()

	def _sync_cost_center_to_accounts(self):
		"""Update cost_center field in Account doctype based on mapping table"""
		for row in self.get("cost_center"):
			if row.account and row.cost_center:
				frappe.db.set_value("Account", row.account, "cost_center", row.cost_center)

	@frappe.whitelist()
	def load_from_accounts(self):
		"""Load all accounts from Account doctype.

		- Loads ALL non-group accounts (with or without cost_center)
		- Preserves existing rows if account still exists
		- Updates cost_center only if it differs from Account
		- Sorted by account_number
		- Does NOT auto-save; leaves doc in unsaved state
		"""
		# Get all non-group accounts for this company, sorted by account_number
		accounts = frappe.get_all(
			"Account",
			filters={
				"company": self.company,
				"is_group": 0,
			},
			fields=["name", "account_number", "cost_center"],
			order_by="account_number asc",
		)

		# Build a map of account -> cost_center from Account doctype
		account_map = {acc.name: acc.cost_center for acc in accounts}
		account_names = [acc.name for acc in accounts]

		# Build existing rows map (account name -> row)
		existing_rows = {}
		for row in self.get("cost_center"):
			if row.account:
				existing_rows[row.account] = row

		# Remove rows whose account no longer exists in Account doctype
		for row in list(self.get("cost_center")):
			if row.account and row.account not in account_map:
				self.remove(row)

		# Update cost_center for existing rows if differs from Account
		for row in self.get("cost_center"):
			if row.account and row.account in account_map:
				acc_cost_center = account_map.get(row.account)
				if acc_cost_center and row.cost_center != acc_cost_center:
					row.cost_center = acc_cost_center

		# Add new accounts that don't have a row yet
		for acc_name in account_names:
			if acc_name not in existing_rows:
				acc_cost_center = account_map.get(acc_name)
				row = self.append("cost_center")
				row.account = acc_name
				row.account_code = frappe.db.get_value("Account", acc_name, "account_number")
				row.cost_center = acc_cost_center
				row.company = self.company
		
		idx = 0
		for d in self.get("cost_center"):
			idx += 1
			d.idx = idx

		# Sort rows by account_code (account_number)
		self.cost_center.sort(key=lambda r: r.account_code or "")

		# Return the updated children for JS rendering
		return self.get("cost_center")
