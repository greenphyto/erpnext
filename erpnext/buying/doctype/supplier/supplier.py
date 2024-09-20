# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
import frappe.defaults
import erpnext
from frappe import _, msgprint
from frappe.contacts.address_and_contact import (
	delete_contact_and_address,
	load_address_and_contact,
)
from frappe.model.naming import set_name_by_naming_series, set_name_from_naming_options, parse_naming_series, NamingSeries

from erpnext.accounts.party import (  # noqa
	get_dashboard_info,
	get_timeline_data,
	validate_party_accounts,
)
from erpnext.utilities.transaction_base import TransactionBase

class Supplier(TransactionBase):
	def get_feed(self):
		return self.supplier_name

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)
		self.load_dashboard_info()

	def before_save(self):
		if not self.on_hold:
			self.hold_type = ""
			self.release_date = ""
		elif self.on_hold and not self.hold_type:
			self.hold_type = "All"

	def load_dashboard_info(self):
		info = get_dashboard_info(self.doctype, self.name)
		self.set_onload("dashboard_info", info)

	def autoname(self):
		supp_master_name = frappe.defaults.get_global_default("supp_master_name")
		if supp_master_name == "Supplier Name":
			self.name = self.supplier_name
		elif supp_master_name == "Naming Series":
			set_name_by_naming_series(self)
		else:
			self.name = set_name_from_naming_options(frappe.get_meta(self.doctype).autoname, self)
		
		self.supplier_id = self.name
		self.set_code()

	def set_code(self, force=False):
		series = self.supplier_code_series or "S0.####"
		if self.supplier_code and not force:
			return
		
		self.supplier_code = parse_naming_series(series, doc=self)
		self.set_account_default()

	def set_account_default(self):
		doc = frappe.get_doc("Buying Settings")
		company = erpnext.get_default_company()
		for d in doc.get("default_supplier_account"):
			series = d.code.replace("...", "")
			if series in self.supplier_code:
				row = self.get("accounts", {"company":company})
				if not row:
					row = self.append("accounts")
					row.account = d.account
					row.company = company

	def on_update(self):
		if not self.naming_series:
			self.naming_series = ""

		self.create_primary_contact()
		self.create_primary_address()

	def validate(self):
		self.flags.is_new_doc = self.is_new()
		self.set_code()
		self.update_series()
		# self.validate_item_supplier()
		if not self.get("account"):
			self.set_account_default()

		# validation for Naming Series mandatory field...
		if frappe.defaults.get_global_default("supp_master_name") == "Naming Series":
			if not self.naming_series:
				msgprint(_("Series is mandatory"), raise_exception=1)

		validate_party_accounts(self)
		self.validate_internal_supplier()

	def after_insert(self):
		self.validate_item_supplier(after_insert=1)


	@frappe.whitelist()
	def get_supplier_group_details(self):
		doc = frappe.get_doc("Supplier Group", self.supplier_group)
		self.payment_terms = ""
		self.accounts = []

		if doc.accounts:
			for account in doc.accounts:
				child = self.append("accounts")
				child.company = account.company
				child.account = account.account

		if doc.payment_terms:
			self.payment_terms = doc.payment_terms

		self.save()

	def validate_internal_supplier(self):
		if not self.is_internal_supplier:
			self.represents_company = ""

		internal_supplier = frappe.db.get_value(
			"Supplier",
			{
				"is_internal_supplier": 1,
				"represents_company": self.represents_company,
				"name": ("!=", self.name),
			},
			"name",
		)

		if internal_supplier:
			frappe.throw(
				_("Internal Supplier for company {0} already exists").format(
					frappe.bold(self.represents_company)
				)
			)

	def create_primary_contact(self):
		from erpnext.selling.doctype.customer.customer import make_contact

		if not self.supplier_primary_contact:
			if self.mobile_no or self.email_id:
				contact = make_contact(self)
				self.db_set("supplier_primary_contact", contact.name)
				self.db_set("mobile_no", self.mobile_no)
				self.db_set("email_id", self.email_id)

	def create_primary_address(self):
		from frappe.contacts.doctype.address.address import get_address_display

		from erpnext.selling.doctype.customer.customer import make_address

		if self.flags.is_new_doc and self.get("address_line1"):
			address = make_address(self)
			address_display = get_address_display(address.name)

			self.db_set("supplier_primary_address", address.name)
			self.db_set("primary_address", address_display)

	def on_trash(self):
		if self.supplier_primary_contact:
			frappe.db.sql(
				"""
				UPDATE `tabSupplier`
				SET
					supplier_primary_contact=null,
					supplier_primary_address=null,
					mobile_no=null,
					email_id=null,
					primary_address=null
				WHERE name=%(name)s""",
				{"name": self.name},
			)

		delete_contact_and_address("Supplier", self.name)

		frappe.db.sql("delete from `tabParty Specific Item` where party_type = 'Supplier' and party = %s ", (self.name))

	def after_rename(self, olddn, newdn, merge=False):
		if frappe.defaults.get_global_default("supp_master_name") == "Supplier Name":
			self.db_set("supplier_name", newdn)
			self.db_set("supplier_id", newdn)

	def update_series(self):
		next_series = get_exists_series(self.supplier_code_series)
		if next_series == self.supplier_code:
			parse_naming_series(self.supplier_code_series, doc=self)

	def validate_item_supplier(self, after_insert=False):
		# create/delete Party Specific Item
		def process(value, typ="Add"):
			data = {
				"party_type":"Supplier",
				"party":self.name,
				"restrict_based_on":"Item",
				"based_on_value":value
			}
			exist = frappe.db.exists("Party Specific Item", data)
			if typ == "Add":
				if exist:
					return exist
				else:
					doc = frappe.new_doc("Party Specific Item")
					doc.update(data)
					doc.insert(ignore_permissions=1)
					return doc.name
			else:
				if not exist:
					return
				else:
					frappe.delete_doc("Party Specific Item", exist)
		old_doc = self.get_doc_before_save()
		if not old_doc:
			if after_insert and self.enable_item_supplier:
				for d in self.get("item_supplier"):
					process(d.item_code, "Add")
			return
		
		old_list = [x.item_code for x in old_doc.get("item_supplier")]

		cur_list = []
		for d in self.get("item_supplier"):
			cur_list.append(d.item_code)
			if not self.enable_item_supplier:
				process(d.item_code, "Delete")
			else:
				process(d.item_code, "Add")

		if self.enable_item_supplier:
			for d in old_doc.get("item_supplier"):
				if d.item_code not in cur_list:
					process(d.item_code, "Delete")
				

@frappe.whitelist()
def get_exists_series(series, doctype="", name="", field_series="", field_code=""):
	# frappe.errprint("Here {}".format(series))
	naming = NamingSeries(series)

	def fake_counter(_prefix, digits):
		count =  naming.get_current_value() + 1
		return str(count).zfill(digits)
	
	res = parse_naming_series(series, number_generator=fake_counter)

	if doctype and name:
		cur_series = frappe.get_value(doctype, name, field_series)
		cur_code = frappe.get_value(doctype, name, field_code)
		if cur_series == series:
			return cur_code

	return res


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_supplier_primary_contact(doctype, txt, searchfield, start, page_len, filters):
	supplier = filters.get("supplier")
	return frappe.db.sql(
		"""
		SELECT
			`tabContact`.name from `tabContact`,
			`tabDynamic Link`
		WHERE
			`tabContact`.name = `tabDynamic Link`.parent
			and `tabDynamic Link`.link_name = %(supplier)s
			and `tabDynamic Link`.link_doctype = 'Supplier'
			and `tabContact`.name like %(txt)s
		""",
		{"supplier": supplier, "txt": "%%%s%%" % txt},
	)
