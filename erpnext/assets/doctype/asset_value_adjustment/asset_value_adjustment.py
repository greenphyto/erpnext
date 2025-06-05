# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, date_diff, flt, formatdate, getdate, add_months

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.assets.doctype.asset.asset import get_depreciation_amount
from erpnext.assets.doctype.asset.depreciation import get_depreciation_accounts


class AssetValueAdjustment(Document):
	def validate(self):
		self.validate_value()
		self.validate_date()
		self.set_current_asset_value()
		self.set_difference_amount()

	def on_submit(self):
		self.make_depreciation_entry()
		self.modify_depreciations()

	def on_cancel(self):
		self.modify_depreciations(cancel=True)

	def validate_date(self):
		asset_purchase_date = frappe.db.get_value("Asset", self.asset, "purchase_date")
		if getdate(self.date) < getdate(asset_purchase_date):
			frappe.throw(
				_("Asset Value Adjustment cannot be posted before Asset's purchase date <b>{0}</b>.").format(
					formatdate(asset_purchase_date)
				),
				title=_("Incorrect Date"),
			)
	
	def validate_value(self):
		if not self.new_asset_value and not self.total_number_of_depreciations:
			frappe.throw(_("The new Asset Value or new Number of Depreciation must be set"))

		not_change_value = flt(self.difference_amount) == 0
		not_change_depreciation = flt(self.total_number_of_depreciations) == flt(self.cur_total_number_of_depreciations)

		if not_change_value and not_change_depreciation:
			frappe.throw(_("Nothing change on the asset value, please check again on your document."))

	def set_difference_amount(self):
		self.new_asset_value = flt(self.new_asset_value) or self.current_asset_value
		self.difference_amount = flt(self.current_asset_value) - flt(self.new_asset_value)

		self.total_number_of_depreciations = flt(self.total_number_of_depreciations) or self.cur_total_number_of_depreciations


	def set_current_asset_value(self):
		if not self.current_asset_value and self.asset:
			self.current_asset_value = get_current_asset_value(self.asset, self.finance_book)

	def make_depreciation_entry(self):
		if not self.difference_amount:
			return
		
		asset = frappe.get_doc("Asset", self.asset)
		(
			fixed_asset_account,
			accumulated_depreciation_account,
			depreciation_expense_account,
		) = get_depreciation_accounts(asset)

		depreciation_cost_center, depreciation_series = frappe.get_cached_value(
			"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
		)

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Depreciation Entry"
		je.naming_series = depreciation_series
		je.posting_date = self.date
		je.company = self.company
		je.remark = "Depreciation Entry against {0} worth {1}".format(self.asset, self.difference_amount)
		je.finance_book = self.finance_book

		credit_entry = {
			"account": accumulated_depreciation_account,
			"credit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center,
		}

		debit_entry = {
			"account": depreciation_expense_account,
			"debit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center,
		}

		accounting_dimensions = get_checks_for_pl_and_bs_accounts()

		for dimension in accounting_dimensions:
			if dimension.get("mandatory_for_bs"):
				credit_entry.update(
					{
						dimension["fieldname"]: self.get(dimension["fieldname"])
						or dimension.get("default_dimension")
					}
				)

			if dimension.get("mandatory_for_pl"):
				debit_entry.update(
					{
						dimension["fieldname"]: self.get(dimension["fieldname"])
						or dimension.get("default_dimension")
					}
				)

		je.append("accounts", credit_entry)
		je.append("accounts", debit_entry)

		je.flags.ignore_permissions = True
		je.submit()

		self.db_set("journal_entry", je.name)
	
	def modify_depreciations(self, cancel=False):
		if cint(self.total_number_of_depreciations) == cint(self.cur_total_number_of_depreciations):
			return
		
		asset = frappe.get_doc("Asset", self.asset)
		asset.clear_depreciation_schedule_ondate(use_date=self.date)
		dep_months_ready = len(asset.schedules)
		accum_dep_amount = 0
		if dep_months_ready:
			depreciation_start_date = asset.schedules[-1].schedule_date
			if not self.difference_amount:
				accum_dep_amount = asset.schedules[-1].accumulated_depreciation_amount
			else:
				accum_dep_amount = asset.gross_purchase_amount - self.new_asset_value

		if not cancel:
			total_number_of_depreciations = self.total_number_of_depreciations
		else:
			total_number_of_depreciations = self.cur_total_number_of_depreciations

		for finance_book in asset.get("finance_books"):
			finance_book.total_number_of_depreciations = total_number_of_depreciations
			month_dep = finance_book.total_number_of_depreciations - dep_months_ready
			start_dep_amount = flt(accum_dep_amount)
			if not self.difference_amount:
				use_amount = asset.gross_purchase_amount - flt(accum_dep_amount)
				depreciable_value = asset.gross_purchase_amount-accum_dep_amount
			else:
				use_amount = self.new_asset_value
				depreciable_value = flt(self.new_asset_value)

			for n in range(cint(month_dep)):
				if finance_book.depreciation_method in ("Straight Line", "Manual"):
					depreciation_amount = (
						(flt(use_amount) - flt(asset.opening_accumulated_depreciation) - flt(finance_book.expected_value_after_useful_life))
					) / (flt(finance_book.total_number_of_depreciations) - flt(asset.number_of_depreciations_booked) - flt(dep_months_ready))

					# add the last value to the last row, based on chat with WQ 03/06/25
					if depreciable_value < depreciation_amount*1.25:
						depreciation_amount = depreciable_value
					
					depreciable_value -= depreciation_amount

				# not yet for percent basis
				# else:
				# 	depreciation_amount = flt(depreciable_value * (flt(row.rate_of_depreciation) / 100))

				schedule_date = add_months(
					depreciation_start_date, (n+1) * cint(finance_book.frequency_of_depreciation)
				)
				if depreciable_value >= 0 and depreciation_amount:
					start_dep_amount += depreciation_amount
					row = asset._add_depreciation_row(
						schedule_date,
						depreciation_amount,
						finance_book.depreciation_method,
						finance_book.finance_book,
						finance_book.idx,
					)
					row.docstatus = 1
					row.accumulated_depreciation_amount = start_dep_amount
					row.insert()
					
		if cancel:
			frappe.delete_doc("Comment", self.comment_reff)
		else:
			comment = "Asset Value Adjustment: {}".format(self.remarks)
			comm = asset.add_comment("Comment", comment)
			self.comment_reff = comm.name

		asset.db_update()


@frappe.whitelist()
def get_current_asset_value(asset, finance_book=None):
	cond = {"parent": asset, "parenttype": "Asset"}
	if finance_book:
		cond.update({"finance_book": finance_book})

	return frappe.db.get_value("Asset Finance Book", cond, "value_after_depreciation")

@frappe.whitelist()
def get_current_asset_data(asset, finance_book=None):
	cond = {"parent": asset, "parenttype": "Asset"}
	if finance_book:
		cond.update({"finance_book": finance_book})

	return frappe.db.get_value("Asset Finance Book", cond, [
		"value_after_depreciation as current_asset_value",
		"value_after_depreciation as new_asset_value",
		"total_number_of_depreciations as cur_total_number_of_depreciations",
		"frequency_of_depreciation as cur_frequency_of_depreciation",
		"depreciation_method as cur_depreciation_method",
		"frequency_of_depreciation",
		"depreciation_method",
		"total_number_of_depreciations"
	], as_dict=1)
