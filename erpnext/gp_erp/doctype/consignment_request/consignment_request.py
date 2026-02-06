# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
import frappe.utils
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.desk.notifications import clear_doctype_notifications
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from frappe.utils import add_days, cint, cstr, flt, get_link_to_form, getdate, nowdate, strip_html
from frappe.utils import safe_abs as abs

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	unlink_inter_company_doc,
	update_linked_doc,
	validate_inter_company_party,
)
from erpnext.accounts.party import get_party_account
from erpnext.controllers.selling_controller import SellingController
from erpnext.manufacturing.doctype.production_plan.production_plan import (
	get_items_for_material_requests,
)
from erpnext.selling.doctype.customer.customer import check_credit_limit
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.get_item_details import get_default_bom
from erpnext.stock.stock_balance import get_reserved_qty, update_bin_qty
from erpnext.stock.doctype.batch.batch import get_batch_no

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


class ConsignmentRequest(SellingController):
	def __init__(self, *args, **kwargs):
		super(ConsignmentRequest, self).__init__(*args, **kwargs)

	def validate(self):
		super(ConsignmentRequest, self).validate()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.set_status()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def on_submit(self):
		self.check_credit_limit()
		frappe.get_doc("Authorization Control").validate_approving_authority(
			self.doctype, self.company, self.base_grand_total, self
		)
		self.create_customer_warehouse()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
		super(ConsignmentRequest, self).on_cancel()

		# Cannot cancel closed SO
		if self.status == "Closed":
			frappe.throw(_("Closed order cannot be cancelled. Unclose to cancel."))

		self.db_set("status", "Cancelled")

	def update_prevdoc_status(self, action):
		pass

	def check_credit_limit(self):
		# if bypass credit limit check is set to true (1) at Consignment Request level,
		# then we need not to check credit limit and vise versa
		if not cint(
			frappe.db.get_value(
				"Customer Credit Limit",
				{"parent": self.customer, "parenttype": "Customer", "company": self.company},
				"bypass_credit_limit_check",
			)
		):
			check_credit_limit(self.customer, self.company)

	def check_modified_date(self):
		mod_db = frappe.db.get_value("Consignment Request", self.name, "modified")
		date_diff = frappe.db.sql("select TIMEDIFF('%s', '%s')" % (mod_db, cstr(self.modified)))
		if date_diff and date_diff[0][0]:
			frappe.throw(_("{0} {1} has been modified. Please refresh.").format(self.doctype, self.name))

	def update_status(self, status):
		self.check_modified_date()
		self.set_status(update=True, status=status)

	def set_indicator(self):
		"""Set indicator for portal"""
		if self.per_billed < 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Not Paid and Not Delivered")

		elif self.per_billed == 100 and self.per_delivered < 100:
			self.indicator_color = "orange"
			self.indicator_title = _("Paid and Not Delivered")

		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def create_customer_warehouse(self):
		from erpnext.stock.doctype.warehouse.warehouse import create_warehouse

		# create parent warehouse if not exists
		parent_name = "Consignment Warehouse"
		parent = frappe.db.exists("Warehouse", {"warehouse_name": parent_name, "company": self.company})
		if not parent:
			parent = create_warehouse(
				parent_name,
				company=self.company,
				is_group=1,
			)

		self.con_warehouse = frappe.db.get_value("Warehouse", {"consignment_request": self.name})
		if not self.con_warehouse:
			warehouse_name = f"Consignment - {self.customer}"
			warehouse = create_warehouse(
				warehouse_name,
				company=self.company,
				consignment_request=self.name,
				is_group=0,
				parent_warehouse=parent,
				return_doc=True,
			)
			warehouse.customer=self.customer
			frappe.msgprint(
				_("Warehouse {0} created for Customer {1}").format(
					get_link_to_form("Warehouse", warehouse.name), self.customer
				)
			)
			self.con_warehouse = warehouse.name

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Orders"),
		}
	)

	return list_context


@frappe.whitelist()
def make_stock_transfer(source_name, target_doc=None):
	def postprocess(source, target):
		target.purpose = "Material Transfer"
		target.stock_entry_type = "Material Transfer"
		target.stock_entry_type_view = "Consignment Transfer"
		target.naming_series = "CON-TRF-.YYYY.-"
		target.from_warehouse = source.set_warehouse
		target.to_warehouse = source.con_warehouse

	def update_item(source_doc, target_doc, source_parent):
		target_doc.s_warehouse = source_parent.set_warehouse
		target_doc.t_warehouse = source_parent.con_warehouse

		# Rate configuration!

	doclist = get_mapped_doc(
		"Consignment Request",
		source_name,
		{
			"Consignment Request": {
				"doctype": "Stock Entry",
				"field_map": {},
				"field_no_map": ["payment_terms_template"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Consignment Request Item": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "consignment_item",
					"parent": "consignment_request",
				},
				"postprocess": update_item,
				# "condition": lambda doc: doc.delivered_qty < doc.qty,
			},
		},
		target_doc,
		postprocess,
		ignore_permissions=1,
	)

	return doclist

@frappe.whitelist()
def make_stock_return(source_name, target_doc=None):
	frappe.msgprint("Make Stock Return")

@frappe.whitelist()
def make_salvage_process(source_name, target_doc=None):
	frappe.msgprint("Make Salvage Process")

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	frappe.msgprint("Make Delivery Note")

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	frappe.msgprint("Make Sales Invoice")