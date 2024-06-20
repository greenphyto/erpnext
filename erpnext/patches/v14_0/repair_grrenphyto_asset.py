import frappe
from frappe.utils import getdate, get_last_day

"""
bench --site test4 execute erpnext.patches.v14_0.repair_grrenphyto_asset.fix_asset_gp
"""
def fix_asset_gp():
	asset1 = "720005-2"
	asset2 = "710011"
	asset3 = "710015"


	# 1
	def update_asset(asset_name, start_date):
		doc = frappe.get_doc("Asset", asset_name)
		start_date = getdate(start_date)
		print("Before", doc.docstatus)
		doc.flags.ignore_links = 1
		doc.db_set("docstatus", 0)
		doc.available_for_use_date = start_date
		doc.purchase_date = start_date
		for d in doc.get("finance_books"):
			d.depreciation_start_date = start_date
		doc.schedules = []
		doc.save()
		doc.submit()

		for d in doc.get("schedules"):
			name = frappe.db.sql("""
			SELECT 
					j.name, parent, a.name AS nm
				FROM
					`tabJournal Entry Account` a
						LEFT JOIN
					`tabJournal Entry` j ON j.name = a.parent
				WHERE
					a.reference_type = 'Asset'
						AND a.reference_name = %s
						AND a.docstatus = 1
						AND j.posting_date BETWEEN %s AND %s        
				limit 1          
			""", (doc.name, getdate(d.schedule_date).replace(day=1), get_last_day(getdate(d.schedule_date))), as_dict=1)
			if name:
				name = name[0]
				print(name)
				d.db_set("journal_entry", name.parent)
		
		doc.set_status()

		# aaset movement
		data = doc.get_asset_movement_data()
		exist = frappe.db.get_value("Asset Movement Item", {"asset":doc.name}, "parent")
		if exist:
			print("Set date", exist, data['transaction_date'])
			frappe.db.set_value("Asset Movement", exist, "transaction_date", data['transaction_date'])


	# update_asset("720005-2", "2021-03-31" )
	# update_asset("710011", "2022-04-14" )
	# update_asset("710015", "2021-05-19" )
	# frappe.throw("OKE")

	# regenereate journal after fix start date
	