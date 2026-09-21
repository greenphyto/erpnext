import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE `tabPart Number Details` pnd
		INNER JOIN `tabPart Number Settings` pns ON pns.name = pnd.parent
		INNER JOIN `tabItem` item ON item.item_code = pnd.code
		INNER JOIN `tabAccount` account
			ON account.company = pns.company
			AND account.account_number = %(account_number)s
		SET pnd.account_code = account.name
		WHERE pnd.parenttype = 'Part Number Settings'
			AND item.item_group = 'Raw Material'
			AND item.rnd_item = 1
		""",
		{"account_number": "126000"},
	)


"""
SELECT
	pns.company,
	pnd.parent AS part_number_settings,
	pnd.code AS item_code,
	item.item_name,
	item.item_group,
	item.rnd_item,
	pnd.account_code AS current_account,
	account.name AS target_account
FROM `tabPart Number Details` pnd
INNER JOIN `tabPart Number Settings` pns ON pns.name = pnd.parent
INNER JOIN `tabItem` item ON item.item_code = pnd.code
INNER JOIN `tabAccount` account
	ON account.company = pns.company
	AND account.account_number = '126000'
WHERE pnd.parenttype = 'Part Number Settings'
	AND item.item_group = 'Raw Material'
	AND item.rnd_item = 1;
"""
