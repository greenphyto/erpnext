import frappe
from frappe.utils import flt

# item_code disesuaikan dengan item Products yang sesuai
DATA = {
	"PR-LV-MSH": {"utilities": 1.6077, "manpower": 2.27},  # Oak (Shepard) ?
	"PR-LV-MNA": {"utilities": 1.8073, "manpower": 2.27},  # Romaine (Napa) ?
	"PR-LV-MEX": {"utilities": 2.1702, "manpower": 2.27},  # Incised (Exmond) 
	"PR-LV-MBE": {"utilities": 1.9546, "manpower": 2.27},  # Butterhead (Bernoulli)
	"PR-LV-TCC": {"utilities": 1.8811, "manpower": 3.41},  # Teen Red Coco
	"PR-AV-SP": {"utilities": 3.4256, "manpower": 4.55},  # Baby Pak Choy
	"PR-LV-BAN": {"utilities": 5.8304, "manpower": 4.55},  # Spinach
	"PR-LV-BAR": {"utilities": 5.2595, "manpower": 4.55},  # Arugula
	"PR-LV-LI": {"utilities": 1.6806, "manpower": 2.27},  # Mambo
	"PR-LV-CO": {"utilities": 1.7522, "manpower": 2.27},  # Coco
	"PR-LV-CR": {"utilities": 1.6211, "manpower": 2.27},  # Crystal
	"PR-AV-KL": {"utilities": 2.2788, "manpower": 2.27},  # Kailan
	"PR-AV-KOM": {"utilities": 1.6716, "manpower": 2.27},  # Koma
	"JTO": {"utilities": 3.7474, "manpower": 3.41},  # JTO (item_code belum ada)
	"PR-AV-NB": {"utilities": 2.0311, "manpower": 2.27},  # Nai Bai
	"PR-AV-PC": {"utilities": 2.2841, "manpower": 2.27},  # Red Summer Pak Choy
}

# expense accounts (by account_number) used to book manpower/utilities as
# additional costs on the finish Manufacture entry
EXPENSE_ACCOUNTS = {
	"manpower": "620500",  # Casual Labour
	"utilities": "650101",  # Water & Utilities - Production
}


def _get_expense_account(company, account_number):
	return frappe.db.get_value(
		"Account",
		{"company": company, "account_number": account_number, "is_group": 0},
		"name",
	)


def _ensure_default_cost_center(account, cost_center):
	"""P&L expense accounts must resolve to a cost center so that stock-entry
	additional-cost GL (manpower/utilities) does not fail with
	'Cost Center is required'. The GP fork reads it from Account.cost_center.
	"""
	if not account or not cost_center:
		return
	if not frappe.db.get_value("Account", account, "cost_center"):
		frappe.db.set_value("Account", account, "cost_center", cost_center, update_modified=False)


"""
bench --site erp-candidate execute erpnext.patches.gp.create_rate_card_for_cogs.execute
"""
def execute():
	company = frappe.defaults.get_global_default("company")

	manpower_account = _get_expense_account(company, EXPENSE_ACCOUNTS["manpower"])
	utilities_account = _get_expense_account(company, EXPENSE_ACCOUNTS["utilities"])

	# ensure the P&L expense accounts resolve to a cost center for GL
	production_cc = frappe.db.get_value("Company", company, "cost_center_for_production")
	_ensure_default_cost_center(manpower_account, production_cc)
	_ensure_default_cost_center(utilities_account, production_cc)

	for item_code, rates in DATA.items():
		if not frappe.db.exists("Item", item_code):
			frappe.logger("rate_card_patch").warning(
				"Rate Card patch: item not found {0}".format(item_code)
			)
			continue

		existing = frappe.db.get_value("Item", item_code, "rate_card")
		if existing:
			# backfill expense accounts and the Harvesting rate on an
			# already-created Rate Card, then save so the workstation/BOM
			# hooks run just like the create path
			doc = frappe.get_doc("Rate Card", existing)
			doc.expense_for_manpower = manpower_account
			doc.expense_for_utilities = utilities_account

			detail = None
			for d in doc.rates:
				if d.operation == "Harvesting":
					detail = d
					break
			if detail is None:
				detail = doc.append("rates", {"operation": "Harvesting"})

			# only fill rates that are still empty so manually-set values
			# are not overwritten on re-run
			if not flt(detail.utilities):
				detail.utilities = rates["utilities"]
			if not flt(detail.manpower):
				detail.manpower = rates["manpower"]

			doc.save(ignore_permissions=True)
			rate_card_name = doc.name
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Rate Card",
					"company": company,
					"title": "Rate Card - {0}".format(item_code),
					"expense_for_manpower": manpower_account,
					"expense_for_utilities": utilities_account,
					"rates": [
						{
							"operation": "Harvesting",
							"utilities": rates["utilities"],
							"manpower": rates["manpower"],
							"machinery": 0,
							"consumable": 0,
						}
					],
				}
			).insert(ignore_permissions=True)
			rate_card_name = doc.name

		# assign via Item.save so the update_bom_item hook fires and pushes the
		# rate-card rates into the BOM operations (official cost path)
		item = frappe.get_doc("Item", item_code)
		item.rate_card = rate_card_name
		item.save(ignore_permissions=True)

	frappe.db.commit()
