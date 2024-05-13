import frappe, erpnext
from erpnext.assets.doctype.asset.asset import get_default_asset_code_data

def execute():
	update_asset_item_expense_account()

"""
bench --site erp.greenphyto.com execute erpnext.patches.v14_0.update_expense_account.update_asset_item_expense_account
"""
def update_asset_item_expense_account():
	items = frappe.db.get_all("Item", {"is_fixed_asset":1}, ['name'])
	for d in items:
		item = frappe.get_doc("Item", d.name)
		if not item.get("asset_code"):
			print(f"Asset code missing for {item.name}")
			continue
		
		print(f"Update {item.name}")
		item.set_asset_category()
		item.save()
		


