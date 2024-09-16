# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	cint,
	comma_and,
	flt,
	formatdate,
	getdate,
	time_diff_in_seconds,
	to_timedelta, cstr
)
from typing import Dict, List
import re


from erpnext.support.doctype.issue.issue import get_holidays


class WorkstationHolidayError(frappe.ValidationError):
	pass


class NotInWorkingHoursError(frappe.ValidationError):
	pass


class OverlapError(frappe.ValidationError):
	pass


class Workstation(Document):
	def autoname(self):
		name = ""
		if self.item_code:
			if not self.operation:
				frappe.throw(_("Operation needed if set item code value"))
			name = f"Farm-{self.item_code}-{self.operation}"
		else:
			if not self.workstation_name:
				frappe.throw(_("Please set workstation name"))
			name = self.workstation_name
			
		existing_wss = frappe.get_all(
			"Workstation", filters={
				"item_code": self.item_code,
				"operation":self.operation,
				"amended_from": ["is", "not set"]}, pluck="name"
		)

		if existing_wss:
			index = self.get_next_version_index(existing_wss)
		else:
			index = 1

		suffix = "%.3i" % index  # convert index to string (1 -> "001")
		ws_name = f"{name}-{suffix}"

		if frappe.db.exists("Workstation", name):
			conflicting_ws = frappe.get_doc("Workstation", name)

			if conflicting_ws.item_code != self.item_code:
				msg = _("A Workstation with name {0} already exists for item {1} and operation {2}.").format(
					frappe.bold(name), frappe.bold(conflicting_ws.item_code), frappe.bold(conflicting_ws.operation)
				)

				frappe.throw(
					_("{0}{1} Did you rename the item? Please contact Administrator / Tech support").format(
						msg, "<br>"
					)
				)

		self.name = ws_name
		self.version = index

	@staticmethod
	def get_next_version_index(existing_ws: List[str]) -> int:
		# split by "/" and "-"
		delimiters = ["/", "-"]
		pattern = "|".join(map(re.escape, delimiters))
		ws_parts = [re.split(pattern, ws_name) for ws_name in existing_ws]

		# filter out BOMs that do not follow the following formats: BOM/ITEM/001, BOM-ITEM-001
		valid_ws_parts = list(filter(lambda x: len(x) > 1 and x[-1], ws_parts))

		# extract the current index from the BOM parts
		if valid_ws_parts:
			# handle cancelled and submitted documents
			indexes = []
			for part in valid_ws_parts:
				temp = cint(part[-1])
				if len(str(temp)) > 3:
					temp = cint(str(temp)[len(str(temp)) - 3:])

				indexes.append(temp)

			index = max(indexes) + 1
		else:
			index = 1

		return index

	def validate(self):
		self.validate_per_kg()
		self.validate_calculation_type()
		self.set_hour_rate()

	def before_save(self):
		self.set_data_based_on_workstation_type()

	def set_hour_rate(self):
		self.hour_rate = (
			flt(self.hour_rate_labour)
			+ flt(self.hour_rate_electricity)
			+ flt(self.hour_rate_consumable)
			+ flt(self.hour_rate_rent)
		)

		self.per_qty_rate = (
			flt(self.per_qty_rate_electricity)
			+ flt(self.per_qty_rate_wages)
			+ flt(self.per_qty_rate_machinery)
			+ flt(self.per_qty_rate_consumable)
		)

	def validate_per_kg(self):
		if self.item_code and self.calculation_type == "Per KG":
			stock_uom = frappe.get_value("Item", self.item_code, "stock_uom")
			if stock_uom != "Kg":
				frappe.throw(_("<b>Per KG</b> calculation only for Item with default uom as <b>Kg</b>"))

	def validate_calculation_type(self):
		if self.calculation_type in ("Per Qty", "Per KG"):
			self.hour_rate = 0
			self.hour_rate_labour = 0
			self.hour_rate_electricity = 0
			self.hour_rate_consumable = 0
			self.hour_rate_rent = 0
		else:
			self.per_qty_rate = 0
			self.per_qty_rate_electricity = 0
			self.per_qty_rate_wages = 0
			self.per_qty_rate_machinery = 0

	@frappe.whitelist()
	def set_data_based_on_workstation_type(self):
		if self.workstation_type:
			fields = [
				"hour_rate_labour",
				"hour_rate_electricity",
				"hour_rate_consumable",
				"hour_rate_rent",
				"hour_rate",
				"description",
			]

			data = frappe.get_cached_value("Workstation Type", self.workstation_type, fields, as_dict=True)

			if not data:
				return

			for field in fields:
				if self.get(field):
					continue

				if value := data.get(field):
					self.set(field, value)

	def on_update(self):
		self.validate_overlap_for_operation_timings()
		self.update_bom_operation()

	def validate_overlap_for_operation_timings(self):
		"""Check if there is no overlap in setting Workstation Operating Hours"""
		for d in self.get("working_hours"):
			existing = frappe.db.sql_list(
				"""select idx from `tabWorkstation Working Hour`
				where parent = %s and name != %s
					and (
						(start_time between %s and %s) or
						(end_time between %s and %s) or
						(%s between start_time and end_time))
				""",
				(self.name, d.name, d.start_time, d.end_time, d.start_time, d.end_time, d.start_time),
			)

			if existing:
				frappe.throw(
					_("Row #{0}: Timings conflicts with row {1}").format(d.idx, comma_and(existing)), OverlapError
				)

	def update_bom_operation(self):
		bom_list = frappe.db.sql(
			"""select DISTINCT parent from `tabBOM Operation`
			where workstation = %s and parenttype = 'routing' """,
			self.name,
		)

		for bom_no in bom_list:
			frappe.db.sql(
				"""update `tabBOM Operation` set hour_rate = %s
				where parent = %s and workstation = %s""",
				(self.hour_rate, bom_no[0], self.name),
			)

	def validate_workstation_holiday(self, schedule_date, skip_holiday_list_check=False):
		if not skip_holiday_list_check and (
			not self.holiday_list
			or cint(frappe.db.get_single_value("Manufacturing Settings", "allow_production_on_holidays"))
		):
			return schedule_date

		if schedule_date in tuple(get_holidays(self.holiday_list)):
			schedule_date = add_days(schedule_date, 1)
			self.validate_workstation_holiday(schedule_date, skip_holiday_list_check=True)

		return schedule_date


@frappe.whitelist()
def get_default_holiday_list():
	return frappe.get_cached_value(
		"Company", frappe.defaults.get_user_default("Company"), "default_holiday_list"
	)


def check_if_within_operating_hours(workstation, operation, from_datetime, to_datetime):
	if from_datetime and to_datetime:

		if not cint(
			frappe.db.get_value("Manufacturing Settings", "None", "allow_production_on_holidays")
		):
			check_workstation_for_holiday(workstation, from_datetime, to_datetime)

		if not cint(frappe.db.get_value("Manufacturing Settings", None, "allow_overtime")):
			is_within_operating_hours(workstation, operation, from_datetime, to_datetime)


def is_within_operating_hours(workstation, operation, from_datetime, to_datetime):
	operation_length = time_diff_in_seconds(to_datetime, from_datetime)
	workstation = frappe.get_doc("Workstation", workstation)

	if not workstation.working_hours:
		return

	for working_hour in workstation.working_hours:
		if working_hour.start_time and working_hour.end_time:
			slot_length = (
				to_timedelta(working_hour.end_time or "") - to_timedelta(working_hour.start_time or "")
			).total_seconds()
			if slot_length >= operation_length:
				return

	frappe.throw(
		_(
			"Operation {0} longer than any available working hours in workstation {1}, break down the operation into multiple operations"
		).format(operation, workstation.name),
		NotInWorkingHoursError,
	)


def check_workstation_for_holiday(workstation, from_datetime, to_datetime):
	holiday_list = frappe.db.get_value("Workstation", workstation, "holiday_list")
	if holiday_list and from_datetime and to_datetime:
		applicable_holidays = []
		for d in frappe.db.sql(
			"""select holiday_date from `tabHoliday` where parent = %s
			and holiday_date between %s and %s """,
			(holiday_list, getdate(from_datetime), getdate(to_datetime)),
		):
			applicable_holidays.append(formatdate(d[0]))

		if applicable_holidays:
			frappe.throw(
				_("Workstation is closed on the following dates as per Holiday List: {0}").format(holiday_list)
				+ "\n"
				+ "\n".join(applicable_holidays),
				WorkstationHolidayError,
			)
