import frappe

# item_code disesuaikan dengan item Products yang sesuai
DATA = {
	"PR-LV-MSH": {"electricity": 1.6077, "manpower": 2.27},  # Oak (Shepard) ?
	"PR-LV-MNA": {"electricity": 1.8073, "manpower": 2.27},  # Romaine (Napa) ?
	"PR-LV-MEX": {"electricity": 2.1702, "manpower": 2.27},  # Incised (Exmond) 
	"PR-LV-MBE": {"electricity": 1.9546, "manpower": 2.27},  # Butterhead (Bernoulli)
	"PR-LV-TCC": {"electricity": 1.8811, "manpower": 3.41},  # Teen Red Coco
	"PR-AV-SP": {"electricity": 3.4256, "manpower": 4.55},  # Baby Pak Choy
	"PR-LV-BAN": {"electricity": 5.8304, "manpower": 4.55},  # Spinach
	"PR-LV-BAR": {"electricity": 5.2595, "manpower": 4.55},  # Arugula
	"PR-LV-LI": {"electricity": 1.6806, "manpower": 2.27},  # Mambo
	"PR-LV-CO": {"electricity": 1.7522, "manpower": 2.27},  # Coco
	"PR-LV-CR": {"electricity": 1.6211, "manpower": 2.27},  # Crystal
	"PR-AV-KL": {"electricity": 2.2573, "manpower": 2.27},  # Kailan
	"PR-AV-KOM": {"electricity": 1.6716, "manpower": 2.27},  # Koma
	"JTO": {"electricity": 3.7474, "manpower": 3.41},  # JTO (item_code belum ada)
	"PR-AV-NB": {"electricity": 2.0311, "manpower": 2.27},  # Nai Bai
	"PR-AV-PC": {"electricity": 2.2841, "manpower": 2.27},  # Red Summer Pak Choy
}

# expense accounts (by account_number) used to book manpower/utilities as
# additional costs on the finish Manufacture entry
EXPENSE_ACCOUNTS = {
	"manpower": "620500",  # Casual Labour
	"electricity": "650101",  # Water & Utilities - Production
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
bench --site test6 execute erpnext.patches.gp.create_rate_card_for_cogs.execute
"""
def execute():
	company = frappe.defaults.get_global_default("company")

	manpower_account = _get_expense_account(company, EXPENSE_ACCOUNTS["manpower"])
	electricity_account = _get_expense_account(company, EXPENSE_ACCOUNTS["electricity"])

	# ensure the P&L expense accounts resolve to a cost center for GL
	production_cc = frappe.db.get_value("Company", company, "cost_center_for_production")
	_ensure_default_cost_center(manpower_account, production_cc)
	_ensure_default_cost_center(electricity_account, production_cc)

	for item_code, rates in DATA.items():
		if not frappe.db.exists("Item", item_code):
			frappe.logger(__name__).warning(
				"Rate Card patch: item not found {0}".format(item_code)
			)
			continue

		existing = frappe.db.get_value("Item", item_code, "rate_card")
		if existing:
			# backfill expense accounts on an already-created Rate Card
			frappe.db.set_value(
				"Rate Card",
				existing,
				{
					"expense_for_manpower": manpower_account,
					"expense_for_electricity": electricity_account,
				},
				update_modified=False,
			)
			rate_card_name = existing
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Rate Card",
					"company": company,
					"title": "Rate Card - {0}".format(item_code),
					"expense_for_manpower": manpower_account,
					"expense_for_electricity": electricity_account,
					"rates": [
						{
							"operation": "Harvesting",
							"electricity": rates["electricity"],
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
