# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt"


import frappe
from frappe.utils import cint


def boot_session(bootinfo):
	"""boot session - send website info if guest"""

	bootinfo.custom_css = frappe.db.get_value("Style Settings", None, "custom_css") or ""

	if frappe.session["user"] != "Guest":

		# multi company
		if frappe.db.get_single_value("Accounts Settings", "enable_switch_company_menu"):
			bootinfo.sysdefaults.company_selected = get_company_selected()
			if bootinfo.sysdefaults.company_selected != "ALL":
				bootinfo.sysdefaults.company_color = frappe.db.get_value("Company", bootinfo.sysdefaults.company_selected, "color") or "#1F272E"
				bootinfo.sysdefaults.company = bootinfo.sysdefaults.company_selected
		else:
			bootinfo.sysdefaults.company_selected = "Disabled"

		update_page_info(bootinfo)
		bootinfo.sysdefaults.territory = frappe.db.get_single_value("Selling Settings", "territory")
		bootinfo.sysdefaults.customer_group = frappe.db.get_single_value(
			"Selling Settings", "customer_group"
		)
		bootinfo.sysdefaults.allow_stale = cint(
			frappe.db.get_single_value("Accounts Settings", "allow_stale")
		)
		bootinfo.sysdefaults.quotation_valid_till = cint(
			frappe.db.get_single_value("CRM Settings", "default_valid_till")
		)

		# if no company, show a dialog box to create a new company
		bootinfo.customer_count = frappe.db.sql("""SELECT count(*) FROM `tabCustomer`""")[0][0]

		if not bootinfo.customer_count:
			bootinfo.setup_complete = (
				frappe.db.sql(
					"""SELECT `name`
				FROM `tabCompany`
				LIMIT 1"""
				)
				and "Yes"
				or "No"
			)

		bootinfo.docs += frappe.db.sql(
			"""select name, default_currency, cost_center, default_selling_terms, default_buying_terms,
			default_letter_head, default_bank_account, enable_perpetual_inventory, country from `tabCompany`""",
			as_dict=1,
			update={"doctype": ":Company"},
		)

		party_account_types = frappe.db.sql(
			""" select name, ifnull(account_type, '') from `tabParty Type`"""
		)
		bootinfo.party_account_types = frappe._dict(party_account_types)

		# non stock item
		bootinfo.sysdefaults.non_stock_item = frappe.db.get_single_value("Buying Settings", "non_stock_item")
		bootinfo.sysdefaults.debit_note_item = frappe.db.get_value("Item", {"debit_note_item":1})
		overide_user_defaults(bootinfo)

def overide_user_defaults(bootinfo):
	company = bootinfo.sysdefaults.company_selected
	if company in ['Disabled', 'ALL']:
		return

	# basic company info
	doc = frappe.get_doc("Company", company)
	bootinfo.user.defaults.company = company
	bootinfo.user.defaults.currency = doc.default_currency
	bootinfo.user.defaults.country = doc.country
	bootinfo.user.defaults.time_zone = doc.time_zone or bootinfo.user.defaults.time_zone

	# price lists
	cur = doc.default_currency
	buying = frappe.db.get_value("Price List", {"buying": 1, "enabled": 1, "currency": cur})
	selling = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1, "currency": cur})
	if buying: bootinfo.user.defaults.buying_price_list = buying
	if selling: bootinfo.user.defaults.selling_price_list = selling

	# letter head
	letter_head, content = frappe.db.get_value("Letter Head", {"company": company, "disabled": 0}, ["name", "content"]) or (None, None)
	if letter_head:
		bootinfo.user.defaults.letter_head = letter_head
		bootinfo.user.defaults.default_letter_head_content = content

	# warehouse and cost center
	wh = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
	cc = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")

	if wh:
		bootinfo.user.defaults.default_warehouse = wh
	if cc:
		bootinfo.user.defaults.cost_center = cc




def update_page_info(bootinfo):
	bootinfo.page_info.update(
		{
			"Chart of Accounts": {"title": "Chart of Accounts", "route": "Tree/Account"},
			"Chart of Cost Centers": {"title": "Chart of Cost Centers", "route": "Tree/Cost Center"},
			"Item Group Tree": {"title": "Item Group Tree", "route": "Tree/Item Group"},
			"Customer Group Tree": {"title": "Customer Group Tree", "route": "Tree/Customer Group"},
			"Territory Tree": {"title": "Territory Tree", "route": "Tree/Territory"},
			"Sales Person Tree": {"title": "Sales Person Tree", "route": "Tree/Sales Person"},
		}
	)

@frappe.whitelist()
def get_company_selected():
	if frappe.db.get_single_value("Accounts Settings", "enable_switch_company_menu"):
		return frappe.db.get_value("User", frappe.session.user, "company_selected") or "ALL"
	else:
		return "Disabled"