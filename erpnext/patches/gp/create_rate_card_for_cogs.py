import frappe
from frappe.utils import flt


DATA = {
	"PR-AV-BRE": {"utilities": 3.4256, "manpower": 4.55},  # (R&D Baby) F1 Pak Choy- Red Summer / Baby Pak Coy
	"PR-AV-BRS": {"utilities": 3.4256, "manpower": 4.55},  # (Baby) F1 Pak Choy- Red Summer / Baby Pak Coy
	"PR-AV-DRE": {"utilities": 1.6899, "manpower": 2.27},  # Komatsuna Dream / Koma
	"PR-AV-KL": {"utilities": 2.2788, "manpower": 2.27},  # F1 Hybrid Kailan / Kailan
	"PR-AV-TA": {"utilities": 3.7474, "manpower": 3.41},  # Japanese Tang Oh / JTO
	"PR-AV-TN": {"utilities": 3.7474, "manpower": 3.41},  # (R&D) Japanese Tang Oh 2 / JTO
	"PR-LV-TNA": {"utilities": 1.8073, "manpower": 2.27},  # (Teen) Romaine Lettuce (Napa RZ) / Romaine
	"PR-LV-TSH": {"utilities": 1.6077, "manpower": 2.27},  # (Teen) Salanova Oak Leaf Lettuce (Shepard RZ Knox) / Oak
	"PR-LV-VOL": {"utilities": 1.9546, "manpower": 2.27},  # (R&D) Butterhead Lettuce (Volare) / Butterhead
	"PR-LV-BLI": {"utilities": 5.8304, "manpower": 4.55},  # (Baby) Spinach (Lizard RZ F1)
	"PR-LV-BLJ": {"utilities": 5.8304, "manpower": 4.55},  # (Baby) Spinach (Lizard RZ F1) 3
	"PR-LV-BAR": {"utilities": 5.2595, "manpower": 4.55},  # (Baby) Arugula Runway Rocket
	"PR-LV-BRU": {"utilities": 5.2595, "manpower": 4.55},  # (Baby) Arugula Runway Rocket 2

	"PR-AV-NB": {"utilities": 2.0311, "manpower": 2.27}, # F1 Nai Bai
	"PR-AV-NBB": {"utilities": 2.0311, "manpower": 2.27}, # (R&D) Nai Bai
	"PR-AV-PC": {"utilities": 2.2841, "manpower": 2.27}, # F1 Pak Choy Red Summer
	"PR-LV-CO": {"utilities": 1.7522, "manpower": 2.27}, # Red Salanova Gem Lettuce (Coconino RZ Knox)
	"PR-LV-CR": {"utilities": 1.6211, "manpower": 2.27}, # Crystal Lettuce
	"PR-LV-LI": {"utilities": 1.6806, "manpower": 2.27}, # Leaf Lettuce (Limambo RZ)
	"PR-LV-TBE": {"utilities": 1.9546, "manpower": 2.27}, # (Teen) Salanova Butterhead Lettuce (Bernoulli RZ)
	"PR-LV-TEX": {"utilities": 2.1702, "manpower": 2.27} # (Teen) Salanova Incised Leaf Lettuce (Exmond RZ Knox)
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
bench --site erp-prod execute erpnext.patches.gp.create_rate_card_for_cogs.execute
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

		title = "Rate Card - {0}".format(item_code)
		# reuse a Rate Card linked to the item, or an orphaned one with the
		# same title from a previous run, so we never insert a duplicate
		existing = frappe.db.get_value("Item", item_code, "rate_card") or frappe.db.get_value(
			"Rate Card", {"title": title}, "name"
		)
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
					"title": title,
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

	# items not listed in DATA should have no rate card: clear it via
	# Item.save so the update_bom_item hook also resets the BOM operations
	other_items = frappe.get_all(
		"Item",
		filters={"rate_card": ["is", "set"], "name": ["not in", list(DATA.keys())]},
		pluck="name",
	)
	for item_code in other_items:
		item = frappe.get_doc("Item", item_code)
		item.rate_card = None
		item.save(ignore_permissions=True)

	frappe.db.commit()
