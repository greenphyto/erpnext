import frappe
from frappe.utils import getdate, get_last_day,add_months, add_days
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
"""
bench --site test4 execute erpnext.patches.v14_0.repair_grrenphyto_asset.fix_asset_gp
"""
def fix_asset_gp():
	asset1 = "720005-2"
	asset2 = "710011"
	asset3 = "710015"

	# post_depreciation_entries(date=getdate("2024-06-05"), asset_category=["ICT Hardware"])

	# 1
	def update_asset(asset_name, start_date):
		doc = frappe.get_doc("Asset", asset_name)
		start_date = getdate(start_date)
		print("Before", doc.docstatus)
		doc.flags.ignore_links = 1
		doc.db_set("docstatus", 0)
		doc.available_for_use_date = start_date
		doc.purchase_date = start_date
		if doc.name == "710011":
			doc.opening_accumulated_depreciation = 1513.57
			doc.number_of_depreciations_booked = 22
		for d in doc.get("finance_books"):
			if doc.name == "710011":
				d.depreciation_start_date = get_last_day("2023-01-31")
			else:
				d.depreciation_start_date = get_last_day(start_date)
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
	update_asset("710011", "2021-05-19" )
	update_asset("710015", "2022-03-14" )
	# frappe.throw("OKE")

	# regenereate journal after fix start date
	assets = ['710011', '710015']
	regen_days = []
	regen_jv = []
	asset_category = []
	data = frappe.db.sql("""
		SELECT 
			j.name, parent, a.name AS nm, j.posting_date
		FROM
			`tabJournal Entry Account` a
				LEFT JOIN
			`tabJournal Entry` j ON j.name = a.parent
		WHERE
			a.reference_type = 'Asset'
				AND a.reference_name in %(data)s
				AND a.docstatus = 1
					  """, {"data":assets}, as_dict=1)
	# 1. find other JV
	for d in assets:
		doc = frappe.get_doc("Asset", d)
		if doc.asset_category not in asset_category:
			asset_category.append(doc.asset_category)

		used_jv = [x.journal_entry for x in  doc.get("schedules") if x.journal_entry]
		for jv in data:
			if jv.name not in used_jv and jv.name not in regen_jv:
				regen_jv.append(jv.name)
				if jv.posting_date not in regen_days:
					regen_days.append(jv.posting_date)

			# if posting date not end date
			if getdate(jv.posting_date).day < add_days(get_last_day(jv.posting_date), -1).day and jv.name not in regen_jv:
				regen_jv.append(jv.name)
				if jv.posting_date not in regen_days:
					regen_days.append(jv.posting_date)

				print(100, jv.name, jv.posting_date)
	
	print("Need regen")
	print(regen_jv)
	print(regen_days)

	# return

	for d in regen_jv:
		doc = frappe.get_doc("Journal Entry", d)
		doc.cancel()
	
	# 2. regenerate others
	for d in regen_days:
		post_depreciation_entries(date=get_last_day(add_months(d, 1)), asset_category=asset_category)

	# post_depreciation_entries(date="2023-11-30", asset_category=asset_category)